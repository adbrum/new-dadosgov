'use client';

import React from 'react';
import { Breadcrumb, Icon } from '@ama-pt/agora-design-system';

export const AdminHeader = () => {
    return (
        <header className="h-64 bg-white border-b border-neutral-100 flex items-center justify-between px-32 sticky top-0 z-40">
            <div className="flex items-center gap-16">
                <Breadcrumb
                    items={[
                        { label: 'Home', url: '/' },
                        { label: 'APIs', url: '#' },
                        { label: 'Formulário de inscrição', url: '#' },
                    ]}
                />
            </div>
            <div className="flex items-center gap-32">
                <div className="flex items-center gap-8 text-neutral-600 text-sm cursor-pointer hover:text-primary-600 transition-colors">
                    <span>Português</span>
                    <Icon name="agora-line-arrow-down" className="w-12 h-12" />
                </div>
                <div className="flex items-center gap-8 text-neutral-600 text-sm cursor-pointer hover:text-primary-600 transition-colors">
                    <Icon name="agora-line-search" className="w-20 h-20" />
                    <span>Pesquisar</span>
                </div>
                <div className="w-40 h-40 rounded-full bg-primary-600 text-white flex items-center justify-center font-bold text-sm shadow-sm transition-transform hover:scale-105">
                    DM
                </div>
            </div>
        </header>
    );
};
