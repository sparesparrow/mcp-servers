#!/usr/bin/env node

const { spawn } = require('child_process');
const { Client } = require('@modelcontextprotocol/sdk/client/index.js');
const { StdioClientTransport } = require('@modelcontextprotocol/sdk/client/stdio.js');

// Start the server
const serverProcess = spawn('python', ['-m', 'mcp_prompt_manager'], {
  stdio: ['pipe', 'pipe', process.stderr]
});

// Connect client to server
async function main() {
  const transport = new StdioClientTransport({
    input: serverProcess.stdout,
    output: serverProcess.stdin
  });

  const client = new Client(
    { name: "test-client", version: "1.0.0" },
    { capabilities: {} }
  );

  try {
    await client.connect(transport);
    console.log('Connected to server');

    console.log('\nTesting prompts/list:');
    const prompts = await client.listPrompts();
    console.log(`Found ${prompts.prompts.length} prompts`);
    console.log(prompts.prompts.map(p => p.name).join(', '));

    console.log('\nTesting resources/list:');
    const resources = await client.listResources();
    console.log(`Found ${resources.resources.length} resources`);
    console.log(resources.resources.map(r => r.name).join(', '));

    console.log('\nTesting tools/list:');
    const tools = await client.listTools();
    console.log(`Found ${tools.tools.length} tools`);
    console.log(tools.tools.map(t => t.name).join(', '));

    if (prompts.prompts.length > 0) {
      const promptName = prompts.prompts[0].name;
      const args = {};
      
      // Get required arguments and give them dummy values
      prompts.prompts[0].arguments.forEach(arg => {
        if (arg.required) {
          args[arg.name] = `test-${arg.name}`;
        }
      });
      
      console.log(`\nTesting prompts/get for '${promptName}':`);
      try {
        const result = await client.getPrompt(promptName, args);
        console.log('Got prompt successfully!');
        console.log('First few characters of the prompt:');
        console.log(result.messages[0].content.text.substring(0, 100) + '...');
      } catch (error) {
        console.error(`Error getting prompt: ${error.message}`);
      }
    }

    console.log('\nTests completed successfully!');
  } catch (error) {
    console.error(`Error: ${error.message}`);
  } finally {
    // Close the connection and kill the server
    await client.close();
    serverProcess.kill();
  }
}

main().catch(error => {
  console.error(`Fatal error: ${error.message}`);
  serverProcess.kill();
  process.exit(1);
});