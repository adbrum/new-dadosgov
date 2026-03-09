import React from 'react';
import { Icon } from '@ama-pt/agora-design-system';
import { Resource } from '@/types/api';

interface DatasetResourcesTableProps {
    resources: Resource[];
}

const formatBytes = (bytes?: number) => {
    if (typeof bytes !== 'number') return '';
    if (bytes === 0) return '0 B';
    const k = 1024;
    const sizes = ['B', 'KB', 'MB', 'GB', 'TB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return `${parseFloat((bytes / Math.pow(k, i)).toFixed(2)).toLocaleString('pt-PT')} ${sizes[i]}`;
};

export const DatasetResourcesTable: React.FC<DatasetResourcesTableProps> = ({ resources }) => {
    // Filter resources by type
    // If type is missing, treat as principal file
    const principalFiles = resources.filter(r => !r.type || r.type === 'main' || r.type === 'file');
    const documentationFiles = resources.filter(r => r.type === 'documentation');

    const renderResourceCard = (resource: Resource) => (
        <div
            key={resource.id}
            className="bg-white border-none shadow-sm p-16 rounded-8"
        >
            <h4 className="text-base font-bold text-neutral-900 mb-8">{resource.title}</h4>
            <div className="flex flex-col gap-4 mt-8">
                <p className="text-sm mb-16">
                    Atualizado em {new Date(resource.created_at).toLocaleDateString('pt-PT', {
                        day: 'numeric',
                        month: 'long',
                        year: 'numeric'
                    })}
                </p>
                <div className="flex items-center gap-2">
                    <a
                        href={resource.url}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="inline-flex items-center gap-8 text-primary-700 font-bold hover:underline"
                    >
                        <Icon name="agora-line-file" className="w-5 h-5" />
                        <span>Formato {resource.format || 'Ficheiro'} {resource.filesize ? `(${formatBytes(resource.filesize)})` : ''}</span>
                    </a>
                    <div className="ml-auto">
                        <a
                            href={resource.url}
                            target="_blank"
                            rel="noopener noreferrer"
                            aria-label={`Descarregar ${resource.title}`}
                        >
                            <Icon name="agora-line-arrow-down-circle" className="w-6 h-6 text-primary-700" />
                        </a>
                    </div>
                </div>
            </div>
        </div>
    );

    return (
        <div className="space-y-32">
            {principalFiles.length > 0 && (
                <div className="space-y-16">
                    <h3 className="font-bold text-neutral-900 text-sm uppercase tracking-wider pb-16">
                        {principalFiles.length} FICHEIROS PRINCIPAIS
                    </h3>
                    <div className="flex flex-col gap-16">
                        {principalFiles.map(renderResourceCard)}
                    </div>
                </div>
            )}

            {documentationFiles.length > 0 && (
                <div className="space-y-16">
                    <h3 className="font-bold text-neutral-900 text-sm uppercase tracking-wider pb-16">
                        {documentationFiles.length} DOCUMENTAÇÃO
                    </h3>
                    <div className="flex flex-col gap-16 px-128 ">
                        {documentationFiles.map(renderResourceCard)}
                    </div>
                </div>
            )}
        </div>
    );
};
