import React from 'react';

interface DatasetInfoProps {
    description: string;
    id: string;
}

export const DatasetInfo: React.FC<DatasetInfoProps> = ({ description, id }) => {
    return (
        <div className="mt-6 space-y-4">
            <div>
                <h4 className="font-bold mb-2">Descrição Completa</h4>
                <p className="text-brand-blue-secondary">{description}</p>
            </div>
            <div>
                <h4 className="font-bold mb-2">Identificador</h4>
                <code className="bg-neutral-100 p-1 rounded">{id}</code>
            </div>
        </div>
    );
};
