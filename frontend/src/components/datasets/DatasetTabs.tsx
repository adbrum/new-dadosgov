import React from 'react';
import { Tabs, Tab, TabHeader, TabBody } from '@ama-pt/agora-design-system';
import { Dataset } from '@/types/api';
import { DatasetResourcesTable } from './DatasetResourcesTable';
import { DatasetInfo } from './DatasetInfo';

interface DatasetTabsProps {
  dataset: Dataset;
}

export const DatasetTabs: React.FC<DatasetTabsProps> = ({ dataset }) => {
  const renderTabBody = (content: React.ReactNode) => (
    <TabBody>
      <div className="relative">
        {/* Visual separator and full-width background */}
        <div
          className="absolute inset-y-0 -mx-4 sm:-mx-8 md:-mx-16 lg:-mx-32 xl:-mx-64 bg-primary-100 border-t border-dashed border-primary-400 z-0"
          aria-hidden="true"
        />

        <div className="relative z-10 pt-64">
          <div className="container mx-auto max-w-5xl">
            {content}
          </div>
        </div>
      </div>
    </TabBody>
  );

  return (
    <div className="mt-64">
      <Tabs>
        <Tab>
          <TabHeader>Ficheiros ({dataset.resources.length})</TabHeader>
          {renderTabBody(<DatasetResourcesTable resources={dataset.resources} />)}
        </Tab>
        <Tab>
          <TabHeader>Reutilizações e APIs ({dataset.metrics.reuses || 0})</TabHeader>
          {renderTabBody(
            <div className="text-neutral-500">
              Conteúdo das reutilizações e APIs.
            </div>
          )}
        </Tab>
        <Tab>
          <TabHeader>Discussões (0)</TabHeader>
          {renderTabBody(
            <div className="text-neutral-500">
              Conteúdo das discussões.
            </div>
          )}
        </Tab>
        <Tab>
          <TabHeader>Recursos comunitários</TabHeader>
          {renderTabBody(
            <div className="text-neutral-500">
              Recursos da comunidade.
            </div>
          )}
        </Tab>
        <Tab>
          <TabHeader>Informação</TabHeader>
          {renderTabBody(
            <DatasetInfo description={dataset.description} id={dataset.id} />
          )}
        </Tab>
      </Tabs>
    </div>
  );
};
