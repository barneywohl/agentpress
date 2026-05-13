'use strict';

const readline = require('node:readline');

function createRL() {
  return readline.createInterface({ input: process.stdin, output: process.stderr });
}

async function ask(question, defaultValue) {
  const rl = createRL();
  const hint = defaultValue !== undefined && defaultValue !== null && defaultValue !== ''
    ? ` [${defaultValue}]`
    : '';
  try {
    return await new Promise((resolve) => {
      rl.question(`? ${question}${hint}: `, (answer) => {
        const v = (answer || '').trim();
        resolve(v || (defaultValue ?? ''));
      });
    });
  } finally {
    rl.close();
  }
}

async function askYesNo(question, defaultYes) {
  const hint = defaultYes ? '[Y/n]' : '[y/N]';
  const rl = createRL();
  try {
    return await new Promise((resolve) => {
      rl.question(`? ${question} ${hint}: `, (answer) => {
        const a = (answer || '').trim().toLowerCase();
        if (a === '') return resolve(!!defaultYes);
        if (['y', 'yes', '1', 'true'].includes(a)) return resolve(true);
        if (['n', 'no', '0', 'false'].includes(a)) return resolve(false);
        // Re-prompt by recursing once
        resolve(askYesNo(question, defaultYes));
      });
    });
  } finally {
    rl.close();
  }
}

module.exports = { ask, askYesNo };
