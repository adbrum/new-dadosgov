'use client';

import React from 'react';
import { Sidebar, SidebarItem, Checkbox, InputSearch, Icon, Toggle, Pill } from '@ama-pt/agora-design-system';

export const OrganizationsFilters = () => {
  const [searchQueries, setSearchQueries] = React.useState<Record<string, string>>({});
  const [activeTab, setActiveTab] = React.useState('reutilizacoes');

  const handleSearchChange = (groupName: string, value: string) => {
    setSearchQueries((prev) => ({
      ...prev,
      [groupName]: value,
    }));
  };

  const filterGroups = [
    { name: 'Organização', type: 'static' }
  ];

  return (
    <div className="h-full organizations-filters">
      {/* Sidebar Type selection as seen in Figma */}
      <div className="mb-64 pr-32 max-w-[592px] flex flex-col gap-16 mt-[32px]">
        {/* Reutilizações */}
        <Toggle
          id="reutilizacoes"
          name="org-filter-type"
          value="reutilizacoes"
          appearance="icon"
          variant="primary"
          hasIcon={true}
          leadingIcon={activeTab === 'reutilizacoes' ? "/Icons/bar_char_white.svg" : "/Icons/bar_chart.svg"}
          leadingIconHover="/Icons/bar_char_white.svg"
          checked={activeTab === 'reutilizacoes'}
          onChange={() => setActiveTab('reutilizacoes')}
          iconOnly={false}
          fullWidth={true}
          className="w-full agora-toggle agora-toggle-icon agora-toggle-icon-primary full-width has-icon"
        >
          <div className="flex items-center gap-12 font-bold text-sm">
            <span className={activeTab === 'reutilizacoes' ? 'text-primary-600 font-bold' : 'text-neutral-900 font-bold'}>
              Reutilizações
            </span>
            <Pill
              variant="neutral"
              appearance="outline"
              circular={false}
              className="text-xs font-medium text-neutral-500 ml-16"
            >
              99
            </Pill>
          </div>
        </Toggle>

        {/* Conjunto de dados */}
        <Toggle
          id="datasets"
          name="org-filter-type"
          value="datasets"
          appearance="icon"
          variant="primary"
          hasIcon
          leadingIcon="agora-line-hardware-settings"
          leadingIconHover="agora-solid-hardware-settings"
          checked={activeTab === 'datasets'}
          onChange={() => setActiveTab('datasets')}
          iconOnly={false}
          fullWidth={true}
          className="w-full"
        >
          <div className="flex items-center gap-12 font-bold text-sm">
            <span className={activeTab === 'datasets' ? 'text-primary-600 font-bold' : 'text-neutral-900 font-bold'}>
              Conjunto de dados
            </span>
            <Pill
              variant="neutral"
              appearance="outline"
              circular={false}
              className="text-xs font-medium text-neutral-500 ml-16"
            >
              99
            </Pill>
          </div>
        </Toggle>

        {/* APIs */}
        <Toggle
          id="apis"
          name="org-filter-type"
          value="apis"
          appearance="icon"
          variant="primary"
          hasIcon
          leadingIcon="agora-line-star"
          leadingIconHover="agora-solid-star"
          checked={activeTab === 'apis'}
          onChange={() => setActiveTab('apis')}
          iconOnly={false}
          fullWidth={true}
          className="w-full"
        >
          <div className="flex items-center gap-12 font-bold text-sm">
            <span className={activeTab === 'apis' ? 'text-primary-600 font-bold' : 'text-neutral-900 font-bold'}>
              APIs
            </span>
            <Pill
              variant="neutral"
              appearance="outline"
              circular={false}
              className="text-xs font-medium text-neutral-500 ml-16"
            >
              99
            </Pill>
          </div>
        </Toggle>
      </div>

      <h2 className="font-bold text-xl text-neutral-900 mt-64 mb-32">Filtros</h2>



      <Sidebar variant="filter" className="font-bold">
        {filterGroups.map((group, index) => {
          return (
            <SidebarItem
              key={index}
              variant="filter"
              item={{
                children: <span className="font-bold">{group.name}</span>,
                hasIcon: true,
                collapsedIconTrailing: 'agora-line-minus-circle',
                collapsedIconHoverTrailing: 'agora-solid-minus-circle',
                expandedIconTrailing: 'agora-line-plus-circle',
                expandedIconHoverTrailing: 'agora-solid-plus-circle'
              }}
            >
              <div className="mt-16">
                <div className="mb-4 mt-8 relative">
                  <InputSearch
                    label="Pesquisar"
                    hideLabel
                    placeholder="Pesquisar"
                    value={searchQueries[group.name] || ''}
                    onChange={(e) => handleSearchChange(group.name, e.target.value)}
                  />
                  <Icon
                    name="agora-solid-search"
                    className="absolute right-12 top-1/2 transform -translate-y-1/2 text-primary-500 w-20 h-20 pointer-events-none"
                    aria-hidden="true"
                  />
                </div>
                <div className="flex flex-col gap-12 mt-16 pb-16">
                  <Checkbox label="Opção 1" value="opt1" className="font-bold" />
                  <Checkbox label="Opção 2" value="opt2" className="font-bold" />
                </div>
              </div>
            </SidebarItem>
          );
        })}
      </Sidebar>
    </div>
  );
};
