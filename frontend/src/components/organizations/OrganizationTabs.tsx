import React from 'react';
import { Tabs, Tab, TabHeader, TabBody } from '@ama-pt/agora-design-system';
import { Organization } from '@/types/api';

interface OrganizationTabsProps {
    organization: Organization;
}

export const OrganizationTabs: React.FC<OrganizationTabsProps> = ({ organization }) => {
    const renderTabBody = (content: React.ReactNode) => (
        <TabBody>
            <div className="relative">
                <div
                    className="absolute inset-y-0 -mx-4 sm:-mx-8 md:-mx-16 lg:-mx-32 xl:-mx-64 bg-primary-100 border-t border-dashed border-primary-400 z-0"
                    aria-hidden="true"
                />
                <div className="relative z-10 py-64">
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
                    <TabHeader>Ficheiros ({organization.metrics?.datasets || 0})</TabHeader>
                    {renderTabBody(
                        <div className="text-neutral-500">
                            Lista de conjuntos de dados publicados por esta organização.
                        </div>
                    )}
                </Tab>
                <Tab>
                    <TabHeader>Reutilizações e APIs ({organization.metrics?.reuses || 0})</TabHeader>
                    {renderTabBody(
                        <div className="text-neutral-500">
                            Reutilizações associadas aos dados desta organização.
                        </div>
                    )}
                </Tab>
                <Tab>
                    <TabHeader>Discussões (0)</TabHeader>
                    {renderTabBody(
                        <div className="text-neutral-500">
                            Conversas e discussões comunitárias.
                        </div>
                    )}
                </Tab>
                <Tab>
                    <TabHeader>Recursos comunitários</TabHeader>
                    {renderTabBody(
                        <div className="flex flex-col gap-16">
                            <h4 className="text-l-semibold text-neutral-900 font-bold">Resumo da Organização</h4>
                            <p className="text-neutral-700">{organization.description || 'Sem descrição detalhada disponível.'}</p>
                            <div className="grid grid-cols-2 gap-32 mt-16">
                                <div>
                                    <span className="text-sm font-semibold text-neutral-500 block">ID</span>
                                    <span className="text-neutral-900">{organization.id}</span>
                                </div>
                                <div>
                                    <span className="text-sm font-semibold text-neutral-500 block">Slug</span>
                                    <span className="text-neutral-900">{organization.slug}</span>
                                </div>
                            </div>
                        </div>
                    )}
                </Tab>
                <Tab>
                    <TabHeader>Informação</TabHeader>
                    {renderTabBody(
                        <div className="flex flex-col gap-16">
                            <h4 className="text-l-semibold text-neutral-900 font-bold">Resumo da Organização</h4>
                            <p className="text-neutral-700">{organization.description || 'Sem descrição detalhada disponível.'}</p>
                            <div className="grid grid-cols-2 gap-32 mt-16">
                                <div>
                                    <span className="text-sm font-semibold text-neutral-500 block">ID</span>
                                    <span className="text-neutral-900">{organization.id}</span>
                                </div>
                                <div>
                                    <span className="text-sm font-semibold text-neutral-500 block">Slug</span>
                                    <span className="text-neutral-900">{organization.slug}</span>
                                </div>
                            </div>
                        </div>
                    )}
                </Tab>
            </Tabs>
        </div>
    );
};
