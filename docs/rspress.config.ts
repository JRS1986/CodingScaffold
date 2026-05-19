import * as path from 'node:path';
import { defineConfig } from '@rspress/core';
import { pluginLlms } from '@rspress/plugin-llms';

export default defineConfig({
  root: path.join(__dirname, 'docs'),
  title: 'CodingScaffold',
  // GitHub Pages serves this project at https://jrs1986.github.io/CodingScaffold/.
  // Without `base`, rspress emits asset URLs at /static/... which resolve to the
  // jrs1986.github.io apex and 404, leaving the deployed site unstyled. The trailing
  // slash matters — rspress normalizes URLs against it.
  base: '/CodingScaffold/',
  builderConfig: {
    server: {
      host: '127.0.0.1',
      port: 3000,
    },
  },
  themeConfig: {
    llmsUI: true,
    socialLinks: [
      {
        icon: "github",
        mode: "link",
        content: "https://github.com/JRS1986/CodingScaffold"
      }
    ]
  },
  plugins: [pluginLlms()]
});
