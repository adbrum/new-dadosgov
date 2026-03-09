'use client';

import React from 'react';
import { Breadcrumb } from '@ama-pt/agora-design-system';

interface PageBannerProps {
  title: React.ReactNode;
  breadcrumbItems: { label: string; url: string }[];
  subtitle?: React.ReactNode;
  children?: React.ReactNode;
  variant?: 'dark' | 'light';
  backgroundImageUrl?: string;
  backgroundPosition?: string;
  image?: {
    src: string;
    alt: string;
    className?: string;
  };
}

const PageBanner: React.FC<PageBannerProps> = ({
  title,
  breadcrumbItems,
  subtitle,
  children,
  variant = 'dark',
  backgroundImageUrl,
  backgroundPosition = 'center',
  image,
}) => {
  const isLight = variant === 'light';

  return (
    <div
      className={`agora-card-highlight-newsletter ${isLight ? 'bg-accent-light' : 'bg-primary-900'}`}
      style={isLight ? {} : {
        backgroundImage: `url("${backgroundImageUrl}")`,
        backgroundSize: 'cover',
        backgroundPosition: backgroundPosition,
        backgroundRepeat: 'no-repeat'
      }}
    >
      <div className="card-container">
        {/* Breadcrumbs Section */}
        <div className="container mx-auto px-4 relative z-10">
          <Breadcrumb
            darkMode={!isLight}
            items={breadcrumbItems}
          />
        </div>

        {/* Content Section (Title & Subtitle) */}
        <div className="card-content relative z-10">
          <div className="title">
            <h1 className={`container mx-auto flex flex-col items-start leading-tight ${typeof title === 'string' ? (isLight ? 'text-primary-900' : 'text-white') : ''}`}>
              {typeof title === 'string' ? (
                <span className="xs:text-xl-bold md:text-2xl-bold xl:text-2xl-bold">{title}</span>
              ) : (
                title
              )}
            </h1>
          </div>
          {subtitle && (
            <div className="subtitle">
              <div className="container mx-auto text-m-regular text-left">
                {typeof subtitle === 'string' ? (
                  <p className={`${isLight ? 'text-neutral-700' : 'text-primary-100'} text-lg leading-relaxed`}>{subtitle}</p>
                ) : (
                  subtitle
                )}
              </div>
            </div>
          )}
        </div>

        {/* Search/Children Section */}
        {(children || image) && (
          <div className="input-container">
            <div className="email-bar">
              <div className="container mx-auto grid xs:grid-cols-4 md:grid-cols-8 xl:grid-cols-12 gap-32 px-4">
                <div className="xs:col-span-4 md:col-span-7 xl:col-span-7">
                  {children}
                </div>
                {image && (
                  <div className="flex justify-end items-center">
                    <div className="image-container mb-16 last:mb-0">
                      <img
                        src={image.src}
                        alt={image.alt}
                        className={`max-w-full h-auto object-contain drop-shadow-xl ${image.className || ''}`}
                      />
                    </div>
                  </div>
                )}
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

export default PageBanner;
