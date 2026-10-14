// Compile TypeScript tests with existing project tooling into a disposable temp directory.
const { mkdtempSync, rmSync } = require('node:fs')
const { tmpdir } = require('node:os')
const { join, resolve } = require('node:path')
const { spawnSync } = require('node:child_process')
const output = mkdtempSync(join(tmpdir(), 'selleros-api-tests-'))
try {
  const root = resolve(__dirname, '..')
  const compile = spawnSync(process.execPath, [join(root, 'node_modules/typescript/bin/tsc'), '--strict', '--skipLibCheck', '--esModuleInterop', '--target', 'ES2022', '--module', 'commonjs', '--moduleResolution', 'node', '--outDir', output, 'tests/api-client.test.ts'], { cwd: root, stdio: 'inherit' })
  if (compile.status !== 0) process.exitCode = compile.status ?? 1
  else process.exitCode = spawnSync(process.execPath, ['--test', join(output, 'tests/api-client.test.js')], { stdio: 'inherit' }).status ?? 1
} finally { rmSync(output, { recursive: true, force: true }) }
