'use client';

import React from 'react';
import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { Icon } from '@ama-pt/agora-design-system';

const menuItems = [
    { label: 'Início', icon: 'agora-line-home', href: '/pages/admin' },
    { label: 'Conjunto de dados', icon: 'agora-line-settings', href: '/pages/admin/datasets' },
    { label: 'Reutilizações', icon: 'agora-line-flag', href: '/pages/admin/reuses' },
    { label: 'Recursos comunitários', icon: 'agora-line-user-group', href: '/pages/admin/community' },
    { label: 'Perfil', icon: 'agora-line-user', href: '/pages/admin/profile' },
    { label: 'Estatísticas', icon: 'agora-line-layers-menu', href: '/pages/admin/stats' },
];

export const AdminSidebar = () => {
    const pathname = usePathname();

    return (
        <aside className="w-[114px] bg-primary-900 flex flex-col items-center py-32 gap-32 h-screen fixed top-0 left-0 z-50">
            {menuItems.map((item) => {
                const isActive = pathname === item.href || (item.href !== '/pages/admin' && pathname?.startsWith(item.href));
                return (
                    <Link
                        key={item.href}
                        href={item.href}
                        className={`flex flex-col items-center gap-8 group w-full px-8 transition-colors ${isActive ? 'text-white' : 'text-primary-300 hover:text-white'
                            }`}
                    >
                        <div className={`p-14 rounded-8 transition-colors ${isActive ? 'bg-primary-600' : 'group-hover:bg-primary-800'}`}>
                            <Icon name={isActive ? item.icon.replace('line', 'solid') : item.icon} className="w-24 h-24" />
                        </div>
                        <span className="text-[12px] text-center font-medium leading-tight">{item.label}</span>
                    </Link>
                );
            })}
        </aside>
    );
};
