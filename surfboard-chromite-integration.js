#!/usr/bin/env node
/**
 * Surfboard + Chromite Integration
 * Connects existing Surfboard Chrome automation with new Chromite Extension system
 * Implements IndyDevDan's atomic design patterns
 */

const { spawn, exec } = require('child_process');
const fs = require('fs');
const path = require('path');

// Import existing Surfboard components
const OptimizedChromePool = require('./optimized-chrome-pool');
const Phase3CredentialManager = require('./phase3-credential-manager');
const ChromiteNativeHost = require('./chromite-native-host');

// Atomic components for Surfboard-Chromite integration
class SurfboardChromeAtoms {
    static createChromeInstanceManager() {
        return {
            instances: new Map(),
            chromePool: null,

            initialize: async function() {
                this.chromePool = new OptimizedChromePool();
                console.log('🏄 Surfboard Chrome Pool initialized');
                return true;
            },

            createChromeWithChromite: async function(instanceId, options = {}) {
                if (!this.chromePool) {
                    await this.initialize();
                }

                const chromeArgs = [
                    '--headless=new',
                    '--no-sandbox',
                    '--disable-dev-shm-usage',
                    '--disable-gpu',
                    '--disable-extensions=false', // Allow extensions!
                    '--load-extension=' + path.resolve('./chromite-extension'),
                    '--disable-background-timer-throttling',
                    '--disable-backgrounding-occluded-windows',
                    '--disable-renderer-backgrounding',
                    '--no-first-run',
                    '--disable-default-apps',
                    ...options.extraArgs || []
                ];

                const userDataDir = `./chrome-instances/${instanceId}`;
                await this.ensureDirectory(userDataDir);

                const debugPort = 9222 + this.instances.size;

                // Detect Chrome installation path
                const chromePaths = [
                    '/mnt/c/Program Files/Google/Chrome/Application/chrome.exe',
                    '/mnt/c/Program Files (x86)/Google/Chrome/Application/chrome.exe',
                    'C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe',
                    'C:\\Program Files (x86)\\Google\\Chrome\\Application\\chrome.exe',
                    'google-chrome',
                    'chromium-browser',
                    'chrome'
                ];

                let chromePath = chromePaths[0]; // Default fallback
                for (const path of chromePaths) {
                    try {
                        if (fs.existsSync(path) || path.includes('google-chrome') || path.includes('chrome')) {
                            chromePath = path;
                            break;
                        }
                    } catch (error) {
                        // Continue checking other paths
                    }
                }

                console.log(`🌐 Using Chrome path: ${chromePath}`);

                const process = spawn(chromePath, [
                    ...chromeArgs,
                    `--user-data-dir=${userDataDir}`,
                    `--remote-debugging-port=${debugPort}`,
                    options.url || 'about:blank'
                ], {
                    detached: false,
                    stdio: ['ignore', 'pipe', 'pipe']
                });

                const instance = {
                    id: instanceId,
                    process: process,
                    debugPort: debugPort,
                    userDataDir: userDataDir,
                    created: Date.now(),
                    taskCount: 0,
                    status: 'starting',
                    chromiteEnabled: true,
                    options
                };

                this.instances.set(instanceId, instance);

                // Wait for Chrome to fully start
                return new Promise((resolve, reject) => {
                    setTimeout(async () => {
                        try {
                            const isReady = await this.verifyInstance(instance);
                            if (isReady) {
                                instance.status = 'ready';
                                console.log(`✅ Surfboard Chrome instance ${instanceId} ready with Chromite`);
                                resolve(instance);
                            } else {
                                reject(new Error('Chrome instance failed to start properly'));
                            }
                        } catch (error) {
                            reject(error);
                        }
                    }, 5000);
                });
            },

            verifyInstance: async function(instance) {
                try {
                    // Check if debug port is accessible
                    const response = await this.makeDebugRequest(instance.debugPort, '/json/version');
                    return response && response.Browser;
                } catch (error) {
                    console.error(`Instance ${instance.id} verification failed:`, error);
                    return false;
                }
            },

            makeDebugRequest: async function(port, endpoint) {
                return new Promise((resolve, reject) => {
                    const http = require('http');
                    const options = {
                        hostname: 'localhost',
                        port: port,
                        path: endpoint,
                        method: 'GET'
                    };

                    const req = http.request(options, (res) => {
                        let data = '';
                        res.on('data', chunk => data += chunk);
                        res.on('end', () => {
                            try {
                                resolve(JSON.parse(data));
                            } catch (error) {
                                reject(error);
                            }
                        });
                    });

                    req.on('error', reject);
                    req.setTimeout(5000, () => reject(new Error('Request timeout')));
                    req.end();
                });
            },

            ensureDirectory: async function(dir) {
                if (!fs.existsSync(dir)) {
                    fs.mkdirSync(dir, { recursive: true });
                }
            },

            destroyInstance: async function(instanceId) {
                const instance = this.instances.get(instanceId);
                if (instance) {
                    try {
                        instance.process.kill();
                        this.instances.delete(instanceId);
                        console.log(`🛑 Destroyed Chrome instance: ${instanceId}`);
                        return true;
                    } catch (error) {
                        console.error(`Failed to destroy instance ${instanceId}:`, error);
                        return false;
                    }
                }
                return false;
            },

            getInstanceStatus: function(instanceId) {
                const instance = this.instances.get(instanceId);
                if (instance) {
                    return {
                        id: instance.id,
                        status: instance.status,
                        debugPort: instance.debugPort,
                        taskCount: instance.taskCount,
                        uptime: Date.now() - instance.created,
                        chromiteEnabled: instance.chromiteEnabled
                    };
                }
                return null;
            }
        };
    }

    static createCredentialIntegration() {
        return {
            credentialManager: null,

            initialize: async function() {
                this.credentialManager = new Phase3CredentialManager();
                await this.credentialManager.initialize();
                console.log('🔐 Credential management integrated');
                return true;
            },

            getChromeCredentials: async function(service = 'default') {
                if (!this.credentialManager) {
                    await this.initialize();
                }

                // Get credentials for Chrome automation
                return await this.credentialManager.getCredentials(service);
            },

            rotateChromeCredentials: async function() {
                if (!this.credentialManager) {
                    await this.initialize();
                }

                // Trigger credential rotation
                return await this.credentialManager.rotateCredentials();
            }
        };
    }
}

// Molecular components for complex integration
class SurfboardChromeMolecules {
    static createAgentChromeOrchestrator() {
        const instanceManager = SurfboardChromeAtoms.createChromeInstanceManager();
        const credentialIntegration = SurfboardChromeAtoms.createCredentialIntegration();

        return {
            initialize: async function() {
                await instanceManager.initialize();
                await credentialIntegration.initialize();
                console.log('🎭 Agent Chrome Orchestrator ready');
            },

            createAgentBrowser: async function(agentId, options = {}) {
                const instanceId = `agent_${agentId}_${Date.now()}`;

                const chromeOptions = {
                    url: options.startUrl || 'about:blank',
                    extraArgs: [
                        '--disable-blink-features=AutomationControlled',
                        '--exclude-switches=enable-automation',
                        '--disable-web-security', // For CORS if needed
                        ...options.extraArgs || []
                    ]
                };

                const instance = await instanceManager.createChromeWithChromite(instanceId, chromeOptions);

                // Associate with agent
                instance.agentId = agentId;
                instance.capabilities = {
                    chromiteExtension: true,
                    nativeMessaging: true,
                    agentIntegration: true,
                    domAutomation: true,
                    formFilling: true,
                    dataExtraction: true
                };

                console.log(`🤖 Created browser for agent ${agentId}: ${instanceId}`);
                return instance;
            },

            getAgentBrowsers: function(agentId) {
                const agentInstances = [];
                for (const [id, instance] of instanceManager.instances) {
                    if (instance.agentId === agentId) {
                        agentInstances.push(instance);
                    }
                }
                return agentInstances;
            },

            destroyAgentBrowsers: async function(agentId) {
                const agentInstances = this.getAgentBrowsers(agentId);
                const destroyPromises = agentInstances.map(instance =>
                    instanceManager.destroyInstance(instance.id)
                );

                const results = await Promise.allSettled(destroyPromises);
                const successful = results.filter(r => r.status === 'fulfilled' && r.value).length;

                console.log(`🧹 Destroyed ${successful}/${agentInstances.length} browsers for agent ${agentId}`);
                return successful;
            },

            getSystemStatus: function() {
                return {
                    totalInstances: instanceManager.instances.size,
                    activeAgents: new Set(Array.from(instanceManager.instances.values()).map(i => i.agentId)).size,
                    instances: Array.from(instanceManager.instances.values()).map(i => ({
                        id: i.id,
                        agentId: i.agentId,
                        status: i.status,
                        uptime: Date.now() - i.created,
                        chromiteEnabled: i.chromiteEnabled
                    }))
                };
            }
        };
    }
}

// Main Surfboard-Chromite Integration
class SurfboardChromeIntegration {
    constructor() {
        this.orchestrator = SurfboardChromeMolecules.createAgentChromeOrchestrator();
        this.nativeHost = null;
        this.isInitialized = false;
    }

    async initialize() {
        if (this.isInitialized) return true;

        console.log('🚀 Initializing Surfboard + Chromite Integration');

        // Initialize orchestrator
        await this.orchestrator.initialize();

        // Start native messaging host
        this.nativeHost = new ChromiteNativeHost();

        this.isInitialized = true;
        console.log('✅ Surfboard + Chromite Integration ready');

        return true;
    }

    async createAgentBrowser(agentId, options = {}) {
        if (!this.isInitialized) await this.initialize();
        return this.orchestrator.createAgentBrowser(agentId, options);
    }

    async destroyAgentBrowsers(agentId) {
        return this.orchestrator.destroyAgentBrowsers(agentId);
    }

    getSystemStatus() {
        return {
            initialized: this.isInitialized,
            nativeHostActive: !!this.nativeHost,
            ...this.orchestrator.getSystemStatus()
        };
    }

    async shutdown() {
        console.log('🛑 Shutting down Surfboard + Chromite Integration');

        // Destroy all instances
        const status = this.orchestrator.getSystemStatus();
        const destroyPromises = status.instances.map(instance =>
            this.orchestrator.destroyInstance(instance.id)
        );

        await Promise.allSettled(destroyPromises);

        this.isInitialized = false;
        console.log('✅ Shutdown complete');
    }
}

// CLI interface
async function main() {
    const args = process.argv.slice(2);
    const integration = new SurfboardChromeIntegration();

    switch (args[0]) {
        case '--start':
            await integration.initialize();
            console.log('🎯 Surfboard + Chromite ready for agent operations');
            break;

        case '--test':
            await integration.initialize();
            console.log('🧪 Running integration test...');

            const testBrowser = await integration.createAgentBrowser('test-agent', {
                startUrl: 'https://example.com'
            });

            console.log('Test browser created:', testBrowser.id);

            setTimeout(async () => {
                await integration.destroyAgentBrowsers('test-agent');
                console.log('✅ Test completed');
                process.exit(0);
            }, 10000);
            break;

        case '--status':
            const status = integration.getSystemStatus();
            console.log('📊 System Status:');
            console.log(JSON.stringify(status, null, 2));
            break;

        case '--shutdown':
            await integration.shutdown();
            break;

        default:
            console.log(`
🏄 Surfboard + ⚡ Chromite Integration

Usage:
  node surfboard-chromite-integration.js [command]

Commands:
  --start     Initialize the integration system
  --test      Run a test browser creation/destruction
  --status    Show current system status
  --shutdown  Shutdown all browser instances

Features:
  ✅ Real Chrome instances with Chromite Extension
  ✅ Native messaging bridge to agent ecosystem
  ✅ Credential management integration
  ✅ Multi-agent browser orchestration
  ✅ Background operation without user interference
`);
    }
}

if (require.main === module) {
    main().catch(console.error);
}

module.exports = SurfboardChromeIntegration;
