'use client';

import React from 'react';
import { useRouter, usePathname, useSearchParams } from 'next/navigation';
import { Sidebar, SidebarItem, Checkbox, InputSearch, Icon } from '@ama-pt/agora-design-system';
import { fetchOrganizations } from '@/services/api';
import { Organization } from '@/types/api';

export const DatasetsFilters = () => {
  const router = useRouter();
  const pathname = usePathname();
  const searchParams = useSearchParams();
  const [organizations, setOrganizations] = React.useState<Organization[]>([]);
  const [isLoading, setIsLoading] = React.useState(true);
  const [searchQueries, setSearchQueries] = React.useState<Record<string, string>>({});

  React.useEffect(() => {
    async function loadOrganizations() {
      try {
        const response = await fetchOrganizations(1, 100);
        setOrganizations(response.data);
      } catch (error) {
        console.error('Failed to load organizations for filters', error);
      } finally {
        setIsLoading(false);
      }
    }
    loadOrganizations();
  }, []);

  const handleOrganizationChange = (orgId: string) => {
    const current = new URLSearchParams(Array.from(searchParams.entries()));
    const currentOrgs = current.getAll('org_id');

    if (currentOrgs.includes(orgId)) {
      current.delete('org_id');
      currentOrgs
        .filter((id) => id !== orgId)
        .forEach((id) => current.append('org_id', id));
    } else {
      current.append('org_id', orgId);
    }

    // Reset page to 1 on filter change
    current.set('page', '1');

    const search = current.toString();
    const query = search ? `?${search}` : '';

    router.push(`${pathname}${query}`);
  };

  const handleSearchChange = (groupName: string, value: string) => {
    setSearchQueries((prev) => ({
      ...prev,
      [groupName]: value,
    }));
  };

  const filterGroups = [
    { name: 'Organização', type: 'dynamic', data: organizations },
    { name: 'Tipo de organização', type: 'static' },
    { name: 'Etiquetas', type: 'static' },
    { name: 'Formatos', type: 'static' },
    { name: 'Licenças', type: 'static' },
    { name: 'Esquema', type: 'static' },
    { name: 'Cobertura espacial', type: 'static' },
    { name: 'Granularidade espacial', type: 'static' },
  ];

  return (
    <div className="h-full">
      <h2 className="font-bold text-xl text-neutral-900 mt-[36px] mb-[64px] pl-[64px]">Filtros</h2>


      <Sidebar variant="filter" className="pl-[64px] font-bold">
        {filterGroups.map((group, index) => {
          const searchQuery = searchQueries[group.name] || '';
          const filteredData = group.data?.filter(item =>
            item.name.toLowerCase().includes(searchQuery.toLowerCase())
          );
          const showSearch = (group.data?.length || 0) > 10;
          const showScroll = (filteredData?.length || 0) > 5;

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
              hasPill={group.name === 'Organização' && searchParams.getAll('org_id').length > 0}
              pillValue={group.name === 'Organização' ? searchParams.getAll('org_id').length : 0}
            >
              <div>
                {showSearch && (
                  <div className="mb-4 mt-8 relative">
                    <InputSearch
                      label="Pesquisar"
                      hideLabel
                      placeholder="Pesquisar"
                      value={searchQuery}
                      onChange={(e) => handleSearchChange(group.name, e.target.value)}
                    />
                    <Icon
                      name="agora-solid-search"
                      className="absolute right-4 top-1/2 transform -translate-y-1/2 text-primary-500 w-5 h-5 pointer-events-none"
                      aria-hidden="true"
                    />
                  </div>
                )}
                <div className={`flex flex-col gap-2 ${showScroll ? 'max-h-[225px] overflow-y-auto' : ''}`}>
                  {group.name === 'Organização' ? (
                    isLoading ? (
                      <p className="text-sm text-neutral-500">A carregar...</p>
                    ) : (
                      (filteredData || []).map((org) => (
                        <Checkbox
                          key={org.id}
                          label={org.name}
                          className="font-bold"
                          value={org.id}
                          name="org_id"
                          checked={searchParams.getAll('org_id').includes(org.id)}
                          onChange={() => handleOrganizationChange(org.id)}
                        />
                      ))
                    )
                  ) : (
                    <>
                      <Checkbox label="Opção 1" value="opt1" className="font-bold" />
                      <Checkbox label="Opção 2" value="opt2" className="font-bold" />
                    </>
                  )}
                </div>
              </div>
            </SidebarItem>
          );
        })}
      </Sidebar>
    </div>
  );
};
