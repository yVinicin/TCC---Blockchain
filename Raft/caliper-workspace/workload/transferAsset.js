'use strict';
const { WorkloadModuleBase } = require('@hyperledger/caliper-core');

class TransferAssetWorkload extends WorkloadModuleBase {
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
        const newOwner = this.txIndex % 2 === 0 ? 'OwnerA' : 'OwnerB';

        const request = {
            contractId: 'basic',
            contractFunction: 'TransferAsset',
            invokerIdentity: 'User1',
            contractArguments: [assetID, newOwner],
            readOnly: false
        };

        await this.sutAdapter.sendRequests(request);
    }

    async cleanupWorkloadModule() {}
}

function createWorkloadModule() {
    return new TransferAssetWorkload();
}

module.exports.createWorkloadModule = createWorkloadModule;

