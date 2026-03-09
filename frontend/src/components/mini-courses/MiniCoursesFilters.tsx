'use client';

import React from 'react';
import { Sidebar, SidebarItem, Checkbox, InputSelect, DropdownSection, DropdownOption } from '@ama-pt/agora-design-system';

export const MiniCoursesFilters = () => {
  const filterGroups = [
    { name: 'Áreas técnicas', type: 'static' },
    { name: 'Perfis', type: 'static' }
  ];

  return (
    <div className="h-full">
      <div className="mb-32">
        <h2 className="font-bold text-[24px] text-neutral-900 mb-16 mt-[270px]">Ordenar</h2>
        <InputSelect
          label="Ordenar"
          id="sort-minicourses"
          defaultValue="az"
          hideLabel={true}
        >
          <DropdownSection name="order">
            <DropdownOption value="az">Ordem alfabética A-Z</DropdownOption>
            <DropdownOption value="za">Ordem alfabética Z-A</DropdownOption>
            <DropdownOption value="recentes">Mais recentes</DropdownOption>
          </DropdownSection>
        </InputSelect>
      </div>

      <div className="mb-6">
        <h2 className="font-bold text-[24px] text-neutral-900 pb-32">Filtrar</h2>
      </div>

      <Sidebar variant="filter">
        {filterGroups.map((group, index) => (
          <SidebarItem
            key={index}
            variant="filter"
            item={{
              children: group.name,
              hasIcon: true,
              collapsedIconTrailing: 'agora-line-minus-circle',
              collapsedIconHoverTrailing: 'agora-solid-minus-circle',
              expandedIconTrailing: 'agora-line-plus-circle',
              expandedIconHoverTrailing: 'agora-solid-plus-circle'
            }}
          >
            <div className="px-6 py-4 bg-white border-t border-neutral-100">
              <div className="flex flex-col gap-2">
                <Checkbox label="Opção 1" value="opt1" />
                <Checkbox label="Opção 2" value="opt2" />
              </div>
            </div>
          </SidebarItem>
        ))}
      </Sidebar>
    </div>
  );
};

