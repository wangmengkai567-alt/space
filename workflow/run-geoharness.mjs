import { appendFileSync, mkdirSync, writeFileSync } from 'node:fs';
import { setTimeout } from 'node:timers/promises';

export const name = 'wuhan-lake-geoharness';
export const inject = ['tools'];

const resultFolder = 'results';
const logPath = `${resultFolder}/deepseek_mcp_calls.jsonl`;
const prefix = 'mcp__geoharness__';

async function run(ctx) {
  mkdirSync(resultFolder, { recursive: true });
  writeFileSync(logPath, JSON.stringify({ type: 'start', host: 'DeepSeek Harness', mode: 'programmatic' }) + '\n');
  const deadline = Date.now() + 100_000;
  while (!ctx.tools.get(`${prefix}list_operators`)) {
    if (Date.now() > deadline) throw new Error('GeoHarness MCP tools did not register');
    await setTimeout(250);
  }

  let nextCall = 0;
  async function call(name, input) {
    const tool = prefix + name;
    const id = `wuhan-${++nextCall}`;
    const log = (event) => appendFileSync(logPath, JSON.stringify({ id, tool, ...event }) + '\n');
    log({ type: 'tool_call', input });
    const batch = await ctx.tools.execute({
      calls: [{ type: 'tool-call', id, name: tool, arguments: JSON.stringify(input) }],
      signal: AbortSignal.timeout(150_000),
    });
    const { result } = batch.results[0];
    if (result.isError) {
      log({ type: 'tool_error', result });
      throw new Error(`${tool}: ${JSON.stringify(result.error ?? result.content)}`);
    }
    const value = result.value.structuredContent;
    if (value === undefined) throw new Error(`${tool} returned no structured MCP result`);
    log({ type: 'tool_result', output: value });
    console.log(`${tool}: ${value.ok === false ? 'FAIL' : 'returned'}`);
    return value;
  }

  await call('list_operators', { names: ['buffer', 'overlay', 'clip_vector', 'zonal_stats'], detail: 'summary' });
  const nodes = [], edges = [];
  const sourceFiles = { lakes: 'lakes.gpkg', built: 'built_up.gpkg', lst: 'lst_c.tif' };
  for (const [id, filename] of Object.entries(sourceFiles)) {
    const args = { name: id, path: `data/inputs/analysis/${filename}`, task_tag: 'wuhan_lake_lst' };
    if (id === 'lst') args.bands = ['lst_c'];
    const ingested = await call('ingest_asset', args);
    if (!ingested.ok) throw new Error(`Asset ingest failed for ${filename}`);
    nodes.push({ id, source: ingested.asset_id });
  }
  function add(id, operator, params, inputs) {
    nodes.push({ id, operator, params });
    for (const [slot, from] of Object.entries(inputs)) edges.push({ from, to: id, slot });
  }
  for (const distance of [150, 450, 600, 900]) {
    add(`b${distance}`, 'buffer', { distance, geodesic: false }, { vector: 'lakes' });
  }
  for (const [band, min, max] of [['near', 150, 450], ['far', 600, 900]]) {
    add(`${band}_ring`, 'overlay', { operation: 'difference' }, { left: `b${max}`, right: `b${min}` });
    add(`${band}_zones`, 'clip_vector', {}, { vector: `${band}_ring`, mask: 'built' });
    add(`${band}_stats`, 'zonal_stats', {
      input_band: 'lst_c', zone_id_field: 'zone_id', column_prefix: 'lst',
      stats: ['mean', 'count', 'valid_fraction'],
    }, { raster: 'lst', zones: `${band}_zones` });
  }
  const dag = { schema_version: 'geoagent-dag/3.0', nodes, edges,
                outputs: ['near_zones', 'far_zones', 'near_stats', 'far_stats'] };
  const task = { task_requirements: [
    { id: 'raster_crs', applies_to: 'lst', attribute: 'crs', relation: 'EQ', value: 'EPSG:32649' },
    { id: 'raster_resolution', applies_to: 'lst', attribute: 'resolution', relation: 'EQ', value: 30 },
  ] };
  const verification = await call('verify_dag', { dag, task });
  let execution;
  if (verification.passed && verification.verified_hash) {
    execution = await call('execute_dag', { dag, verified_hash: verification.verified_hash, output_dir: 'outputs' });
  }
  const trace = await call('export_trace', { profile: 'full' });
  if (!execution?.ok || !execution.l4.passed || !trace.ok) {
    throw new Error(`GeoHarness did not pass all gates. See ${logPath}`);
  }
  console.log(JSON.stringify({ run_id: execution.run_id, verified_hash: execution.verified_hash, trace }));
}

export function apply(ctx) {
  const exit = ctx.get('appExit');
  if (!exit) throw new Error('Start this plugin with the dsh launcher');
  void run(ctx).then(() => exit(0), (error) => {
    console.error(error.message);
    exit(1);
  });
}
