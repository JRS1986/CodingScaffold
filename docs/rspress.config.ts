import * as path from 'node:path';
import { defineConfig } from '@rspress/core';

export default defineConfig({
  root: path.join(__dirname, 'docs'),
  title: 'CodingScaffold',
  builderConfig: {
    server: {
      host: '127.0.0.1',
      port: 3000,
    },
  },
  themeConfig: {
    socialLinks: [
      {
        icon: "github",
        mode: "link",
        content: "https://github.com/JRS1986/CodingScaffold"
      }
    ]
  },
});
