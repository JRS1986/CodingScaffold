import { OpenMultiAgent } from '@jackchen_me/open-multi-agent'
import type { AgentConfig } from '@jackchen_me/open-multi-agent'

const explorer: AgentConfig = {
  name: 'explorer',
  model: process.env.ROUTINE_MODEL ?? 'replace-me-routine-model',
  systemPrompt: 'Map relevant files, commands, dependencies, and risks. Do not edit.',
  tools: ['file_read', 'grep', 'glob'],
}

const planner: AgentConfig = {
  name: 'planner',
  model: process.env.HEAVY_LIFT_MODEL ?? 'replace-me-heavy-lift-model',
  systemPrompt: 'Break the goal into a small task DAG with explicit verification.',
  tools: ['file_read', 'grep'],
}

const implementer: AgentConfig = {
  name: 'implementer',
  model: process.env.ROUTINE_MODEL ?? 'replace-me-routine-model',
  systemPrompt: 'Make bounded edits only after scope is clear. Run narrow checks.',
  tools: ['bash', 'file_read', 'file_write', 'file_edit', 'grep'],
}

const reviewer: AgentConfig = {
  name: 'reviewer',
  model: process.env.HEAVY_LIFT_MODEL ?? 'replace-me-heavy-lift-model',
  systemPrompt: 'Review for regressions, missing tests, security, and maintainability. Do not edit.',
  tools: ['file_read', 'grep'],
}

const goal =
  process.argv.slice(2).join(' ') ||
  'Inspect this repository and propose one safe, small improvement with verification.'

const orchestrator = new OpenMultiAgent({
  defaultModel: process.env.HEAVY_LIFT_MODEL ?? 'replace-me-heavy-lift-model',
  onProgress: (event) => console.log(event.type, event.agent ?? event.task ?? ''),
})

const team = orchestrator.createTeam('coding-scaffold-team', {
  name: 'coding-scaffold-team',
  agents: [explorer, planner, implementer, reviewer],
  sharedMemory: true,
})

const planOnly = process.env.PLAN_ONLY !== '0'
const result = await orchestrator.runTeam(team, goal, { planOnly })

console.log(JSON.stringify({
  success: result.success,
  planOnly,
  totalTokenUsage: result.totalTokenUsage,
  tasks: result.tasks,
}, null, 2))
