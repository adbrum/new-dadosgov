'use client';

import React, { useRef, useState } from 'react';
import Link from 'next/link';
import NextImage from 'next/image';
import { useRouter, usePathname } from 'next/navigation';
import {
  Header as AgoraHeader,
  Brand,
  Logo,
  GeneralBar,
  Areas,
  Area,
  Languages,
  Language,
  Unauthenticated,
  UnauthenticatedLink,
  NavigationBar,
  NavigationLink,
  NavigationRoot,
} from '@ama-pt/agora-design-system';

export const Header = () => {
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const headerRef = useRef<any>(null);
  const router = useRouter();
  const pathname = usePathname();

  const [selectedLanguage, setSelectedLanguage] = useState('pt');
  const [selectedArea, setSelectedArea] = useState(
    pathname === '/pages/login' || pathname === '/pages/register' ? '2' : '1'
  );

  React.useEffect(() => {
    if (pathname === '/pages/login' || pathname === '/pages/register') {
      setSelectedArea('2');
    } else {
      setSelectedArea('1');
    }

    // Force close the responsive menu on route change
    const closeMenu = () => {
      // 1. Try via design system ref
      if (headerRef.current?.closeResponsiveMenu) {
        headerRef.current.closeResponsiveMenu();
      }

      // 2. Fallback: Try to trigger click on the close button in the modal/menu
      // The design system uses specific classes for the close button
      const closeButton = document.querySelector(
        '.agora-header-navigation-modal [aria-label="Fechar"], .agora-header-navigation-modal button.agora-modal-close'
      ) as HTMLButtonElement;
      if (closeButton) {
        closeButton.click();
      }
    };

    // Small timeout to ensure the route change has started and the DOM is accessible
    const timer = setTimeout(closeMenu, 100);
    return () => clearTimeout(timer);
  }, [pathname]);

  const languages = [
    { value: 'pt', label: 'Português', abbr: 'PT' },
    { value: 'en', label: 'English', abbr: 'EN' },
    { value: 'es', label: 'Español', abbr: 'ES' },
    { value: 'fr', label: 'Français', abbr: 'FR' },
  ];

  const areas = [
    { value: '1', label: 'Portal' },
    { value: '2', label: 'Iniciar Sessão' },
  ];

  const currentLangLabel =
    languages.find((l) => l.value === selectedLanguage)?.label || 'Português';
  const currentAreaLabel =
    areas.find((a) => a.value === selectedArea)?.label || 'Portal';

  const handleLinkClick = (e: React.MouseEvent<HTMLAnchorElement>, href: string) => {
    // Force close the menu immediately
    if (headerRef.current?.closeResponsiveMenu) {
      headerRef.current.closeResponsiveMenu();
    }

    // Fallback close
    const closeButton = document.querySelector(
      '.agora-header-navigation-modal [aria-label="Fechar"], .agora-header-navigation-modal button.agora-modal-close'
    ) as HTMLButtonElement;
    if (closeButton) {
      closeButton.click();
    }

    // In mobile, sometimes we need to manually trigger the router to ensure it happens after the menu closes
    if (href !== '#') {
      router.push(href);
    }
  };

  if (pathname?.startsWith('/pages/admin')) {
    return null;
  }

  return (
    <header className="sticky top-0 z-sticky">
      <AgoraHeader ref={headerRef}>
        <Brand>
          <Logo>
            <Link href="/" className="flex items-center">
              <NextImage
                src="/Logos/logo.png"
                alt="dados.gov"
                height={43}
                width={251}
                priority
              />
            </Link>
          </Logo>
        </Brand>

        <GeneralBar aria-label="Opções navegação geral">
          <Areas
            aria-label="Áreas do portal"
            // @ts-ignore - Prop label does exist in component logic
            label={currentAreaLabel}
            onChange={(area: string) => setSelectedArea(area)}
          >
            <Area
              value="1"
              label="Portal"
              onClick={() => router.push('/')}
              active={selectedArea === '1'}
            />
            <Area
              value="2"
              label="Iniciar Sessão"
              onClick={() => router.push('/pages/login')}
              active={selectedArea === '2'}
            />
          </Areas>

          <Languages
            aria-label="Selecionar idioma"
            // @ts-ignore - Prop label does exist in component logic
            label={currentLangLabel}
            onChange={(lang: string) => setSelectedLanguage(lang)}
          >
            <Language
              value="pt"
              label="Português"
              abbr="PT"
              checked={selectedLanguage === 'pt'}
            />
            <Language
              value="en"
              label="English"
              abbr="EN"
              checked={selectedLanguage === 'en'}
            />
            <Language
              value="es"
              label="Español"
              abbr="ES"
              checked={selectedLanguage === 'es'}
            />
            <Language
              value="fr"
              label="Français"
              abbr="FR"
              checked={selectedLanguage === 'fr'}
            />
          </Languages>

          <Unauthenticated label="Inscrever-se" aria-label="Registar">
            <UnauthenticatedLink
              hasIcon
              leadingIcon="agora-line-user"
              leadingIconHover="agora-solid-user"
            >
              <Link href="/pages/register">Inscrever-se</Link>
            </UnauthenticatedLink>
          </Unauthenticated>
        </GeneralBar>

        <NavigationBar
          responsiveMenuLabel="Menu"
          responsiveMenuAriaLabel="Abrir menu"
          responsiveMenuBackToRootLabel="Voltar ao início"
          modalMenuLabel="Navegação Principal"
          modalAriaLabel="Menu de navegação"
          modalCloseLabel="Fechar"
        >
          <NavigationRoot label="Contribuir">
            <NavigationLink appearance="link">
              <a href="#" onClick={(e) => handleLinkClick(e, '#')}>
                Novo Conjunto de Dados
              </a>
            </NavigationLink>
            <NavigationLink appearance="link">
              <a href="#" onClick={(e) => handleLinkClick(e, '#')}>
                Nova API
              </a>
            </NavigationLink>
            <NavigationLink appearance="link">
              <a href="#" onClick={(e) => handleLinkClick(e, '#')}>
                Nova Reutilização
              </a>
            </NavigationLink>
            <NavigationLink appearance="link">
              <a href="#" onClick={(e) => handleLinkClick(e, '#')}>
                Nova Organização
              </a>
            </NavigationLink>
            <NavigationLink appearance="link">
              <a
                href="/pages/support"
                onClick={(e) => {
                  e.preventDefault();
                  handleLinkClick(e, '/pages/support');
                }}
              >
                Contactar
              </a>
            </NavigationLink>
          </NavigationRoot>

          <NavigationRoot label="Explorar">
            <NavigationLink appearance="link">
              <a
                href="/pages/datasets"
                onClick={(e) => {
                  e.preventDefault();
                  handleLinkClick(e, '/pages/datasets');
                }}
              >
                Conjuntos de dados
              </a>
            </NavigationLink>
            <NavigationLink appearance="link">
              <a href="#" onClick={(e) => handleLinkClick(e, '#')}>
                HVDs
              </a>
            </NavigationLink>
            <NavigationLink appearance="link">
              <a href="#" onClick={(e) => handleLinkClick(e, '#')}>
                APIs
              </a>
            </NavigationLink>
            <NavigationLink appearance="link">
              <a
                href="/pages/reuses"
                onClick={(e) => {
                  e.preventDefault();
                  handleLinkClick(e, '/pages/reuses');
                }}
              >
                Reutilizações
              </a>
            </NavigationLink>
            <NavigationLink appearance="link">
              <a
                href="/pages/organizations"
                onClick={(e) => {
                  e.preventDefault();
                  handleLinkClick(e, '/pages/organizations');
                }}
              >
                Organizações
              </a>
            </NavigationLink>
            <NavigationLink appearance="link">
              <a href="#" onClick={(e) => handleLinkClick(e, '#')}>
                Data Stories
              </a>
            </NavigationLink>
          </NavigationRoot>

          <NavigationRoot label="Conhecimento">
            <NavigationLink appearance="link">
              <a
                href="/pages/about-open-data"
                onClick={(e) => {
                  e.preventDefault();
                  handleLinkClick(e, '/pages/about-open-data');
                }}
              >
                Sobre dados abertos
              </a>
            </NavigationLink>
            <NavigationLink appearance="link">
              <a href="#" onClick={(e) => handleLinkClick(e, '#')}>
                Como publicar dados?
              </a>
            </NavigationLink>
            <NavigationLink appearance="link">
              <a href="#" onClick={(e) => handleLinkClick(e, '#')}>
                Como reutilizar dados?
              </a>
            </NavigationLink>
            <NavigationLink appearance="link">
              <a href="#" onClick={(e) => handleLinkClick(e, '#')}>
                O que é o dados.gov
              </a>
            </NavigationLink>
            <NavigationLink appearance="link">
              <a href="#" onClick={(e) => handleLinkClick(e, '#')}>
                Desenvolvimento
              </a>
            </NavigationLink>
            <NavigationLink appearance="link">
              <a href="#" onClick={(e) => handleLinkClick(e, '#')}>
                Publicações
              </a>
            </NavigationLink>
            <NavigationLink appearance="link">
              <a
                href="/pages/article"
                onClick={(e) => {
                  e.preventDefault();
                  handleLinkClick(e, '/pages/article');
                }}
              >
                Notícias
              </a>
            </NavigationLink>
            <NavigationLink appearance="link">
              <a
                href="/pages/mini-courses"
                onClick={(e) => {
                  e.preventDefault();
                  handleLinkClick(e, '/pages/mini-courses');
                }}
              >
                Minicursos
              </a>
            </NavigationLink>
          </NavigationRoot>
        </NavigationBar>
      </AgoraHeader>
    </header>
  );
};
