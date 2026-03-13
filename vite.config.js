import { execSync } from 'node:child_process';
import { readFileSync } from 'node:fs';
import react from '@vitejs/plugin-react';
import { defineConfig } from 'vite';

const packageJson = JSON.parse(
  readFileSync(new URL('./package.json', import.meta.url), 'utf8')
);

function getGitSha() {
  try {
    return execSync('git rev-parse --short HEAD', {
      stdio: ['ignore', 'pipe', 'ignore']
    }).toString().trim();
  } catch {
    return 'nogit';
  }
}

const buildTime = new Date().toISOString();
const buildId = `${packageJson.version}-${buildTime}-${getGitSha()}`;

function buildMetadataPlugin() {
  return {
    name: 'build-metadata',
    generateBundle() {
      this.emitFile({
        type: 'asset',
        fileName: 'version.json',
        source: JSON.stringify(
          {
            version: packageJson.version,
            buildId,
            builtAt: buildTime
          },
          null,
          2
        )
      });
    }
  };
}

export default defineConfig({
  plugins: [react(), buildMetadataPlugin()],
  define: {
    __APP_VERSION__: JSON.stringify(packageJson.version),
    __APP_BUILD_ID__: JSON.stringify(buildId),
    __APP_BUILD_TIME__: JSON.stringify(buildTime)
  }
});
