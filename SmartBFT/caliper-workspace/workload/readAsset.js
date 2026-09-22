'use strict';
const { WorkloadModuleBase } = require('@hyperledger/caliper-core');

class ReadAssetWorkload extends WorkloadModuleBase {
    constructor() {
        super();
        this.txIndex = 0;
        this.assetsPerWorker = 0;
    }

    async initializeWorkloadModule(workerIndex, totalWorkers, roundIndex, roundArguments, sutAdapter, sutContext) {
        await super.initializeWorkloadModule(workerIndex, totalWorkers, roundIndex, roundArguments, sutAdapter, sutContext);
        // Cada worker criou (totalAssets / totalWorkers) assets no warm-up
        const totalAssets = this.roundArguments.totalAssets || 1000;
        this.assetsPerWorker = Math.floor(totalAssets / totalWorkers);
    }

    async submitTransaction() {
        this.txIndex++;
        // Rotaciona apenas entre os assets criados por este worker
        const index = (this.txIndex % this.assetsPerWorker) + 1;
        const assetID = `warmup_asset_w${this.workerIndex}_${index}`;

        const request = {
            contractId: 'basic',
            contractFunction: 'ReadAsset',
            invokerIdentity: 'User1',
            contractArguments: [assetID],
            readOnly: true
        };

        await this.sutAdapter.sendRequests(request);
    }

    async cleanupWorkloadModule() {}
}

function createWorkloadModule() {
    return new ReadAssetWorkload();
}

module.exports.createWorkloadModule = createWorkloadModule;

