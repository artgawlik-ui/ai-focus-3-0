import {build, context} from 'esbuild';
import {cp, readFile, rm, mkdir, writeFile} from 'node:fs/promises';
import {dirname, resolve, relative, sep} from 'node:path';
import {fileURLToPath} from 'node:url';

const root = resolve(dirname(fileURLToPath(import.meta.url)), '..');
const outdir = resolve(root, 'dist');
const watch = process.argv.includes('--watch');
if (process.argv.slice(2).some(arg => arg !== '--watch')) throw new Error('Unknown build argument');
await rm(outdir, {recursive: true, force: true});
await mkdir(outdir, {recursive: true});
await cp(resolve(root, 'public'), outdir, {recursive: true});
const template = await readFile(resolve(root, 'index.html'), 'utf8');
const entryTag = '<script type="module" src="/src/main.tsx"></script>';
if (!template.includes(entryTag)) throw new Error('Missing HTML entry point');
const assetURL = output => {
  const name = relative(outdir, resolve(root, output)).split(sep).join('/');
  if (name.startsWith('../')) throw new Error('Asset outside output directory');
  return '/' + name;
};
const options = {
  absWorkingDir: root, entryPoints: ['src/main.tsx'], outdir,
  bundle: true, format: 'esm', platform: 'browser', target: 'es2022',
  jsx: 'automatic', minify: !watch, metafile: true,
  entryNames: 'assets/[name]-[hash]', assetNames: 'assets/[name]-[hash]',
  define: {'process.env.NODE_ENV': JSON.stringify(watch ? 'development' : 'production')},
  plugins: [{name: 'spa-html', setup(builder) {
    builder.onEnd(async result => {
      if (result.errors.length) return;
      const entry = Object.entries(result.metafile.outputs)
        .find(([, info]) => info.entryPoint === 'src/main.tsx');
      if (!entry) throw new Error('Missing bundled entry point');
      const [js, info] = entry;
      const css = info.cssBundle ? `<link rel="stylesheet" href="${assetURL(info.cssBundle)}"/>` : '';
      const html = template.replace(entryTag,
        `${css}<script type="module" src="${assetURL(js)}"></script>`);
      await writeFile(resolve(outdir, 'index.html'), html);
    });
  }}],
};
if (watch) {
  const builder = await context(options);
  await builder.watch();
  console.log('Watching frontend sources. Serve dist through the existing backend on port 8000; reload the browser after changes.');
} else {
  await build(options);
}
