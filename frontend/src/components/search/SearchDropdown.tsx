"use client";

import { useState, useRef, useEffect } from "react";
import { useRouter } from "next/navigation";
import { InputSearchBar } from "@ama-pt/agora-design-system";

type SearchType = "datasets" | "reuses" | "organizations";

interface SearchOption {
  type: SearchType;
  label: string;
  icon: string;
}

const SEARCH_OPTIONS: SearchOption[] = [
  { type: "datasets", label: "conjuntos de dados", icon: "\u{1F4CA}" },
  { type: "reuses", label: "reutilizações", icon: "\u{1F4C8}" },
  { type: "organizations", label: "organizações", icon: "\u{1F3E2}" },
];

interface SearchDropdownProps {
  id: string;
  darkMode?: boolean;
  placeholder?: string;
  label?: string;
  hasVoiceActionButton?: boolean;
}

export default function SearchDropdown({
  id,
  darkMode = false,
  placeholder = "Pesquisar datasets, organizações, reutilizações...",
  label = "Pesquisar",
  hasVoiceActionButton = false,
}: SearchDropdownProps) {
  const router = useRouter();
  const [query, setQuery] = useState("");
  const [isOpen, setIsOpen] = useState(false);
  const [activeIndex, setActiveIndex] = useState(-1);
  const wrapperRef = useRef<HTMLDivElement>(null);

  // Close dropdown when clicking outside
  useEffect(() => {
    function handleClickOutside(event: MouseEvent) {
      if (
        wrapperRef.current &&
        !wrapperRef.current.contains(event.target as Node)
      ) {
        setIsOpen(false);
      }
    }
    document.addEventListener("mousedown", handleClickOutside);
    return () =>
      document.removeEventListener("mousedown", handleClickOutside);
  }, []);

  const navigateToSearch = (type: SearchType) => {
    const q = query.trim();
    if (q) {
      router.push(
        `/pages/search?q=${encodeURIComponent(q)}&type=${type}`,
      );
      setIsOpen(false);
      setQuery("");
    }
  };

  const handleInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    setQuery(e.target.value);
    setIsOpen(e.target.value.trim().length > 0);
    setActiveIndex(-1);
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (!isOpen) {
      if (e.key === "Enter" && query.trim()) {
        setIsOpen(true);
      }
      return;
    }

    switch (e.key) {
      case "ArrowDown":
        e.preventDefault();
        setActiveIndex((prev) =>
          prev < SEARCH_OPTIONS.length - 1 ? prev + 1 : 0,
        );
        break;
      case "ArrowUp":
        e.preventDefault();
        setActiveIndex((prev) =>
          prev > 0 ? prev - 1 : SEARCH_OPTIONS.length - 1,
        );
        break;
      case "Enter":
        e.preventDefault();
        if (activeIndex >= 0) {
          navigateToSearch(SEARCH_OPTIONS[activeIndex].type);
        } else {
          navigateToSearch("datasets");
        }
        break;
      case "Escape":
        setIsOpen(false);
        setActiveIndex(-1);
        break;
    }
  };

  const handleSearchActivate = () => {
    if (query.trim()) {
      navigateToSearch("datasets");
    }
  };

  return (
    <div ref={wrapperRef} className="relative">
      <InputSearchBar
        label={label}
        placeholder={placeholder}
        id={id}
        value={query}
        onChange={handleInputChange}
        onKeyDown={handleKeyDown}
        onSearchActivate={handleSearchActivate}
        onFocus={() => {
          if (query.trim()) setIsOpen(true);
        }}
        darkMode={darkMode}
        hasVoiceActionButton={hasVoiceActionButton}
        voiceActionAltText="Pesquisar por voz"
        searchActionAltText="Pesquisar"
        autoComplete="off"
      />

      {/* Dropdown */}
      {isOpen && query.trim() && (
        <div className="absolute z-50 w-full mt-4 bg-white rounded-8 shadow-lg border border-neutral-200 overflow-hidden">
          <ul className="list-none m-0 p-0" role="listbox">
            {SEARCH_OPTIONS.map((option, index) => (
              <li
                key={option.type}
                role="option"
                aria-selected={activeIndex === index}
                className={`flex items-center gap-12 px-16 py-12 cursor-pointer border-b border-neutral-100 last:border-b-0 transition-colors ${
                  activeIndex === index
                    ? "bg-primary-50 text-primary-700"
                    : "hover:bg-neutral-50"
                }`}
                onMouseEnter={() => setActiveIndex(index)}
                onClick={() => navigateToSearch(option.type)}
              >
                <span className="text-base" aria-hidden="true">
                  {option.icon}
                </span>
                <span className="flex-1 text-s-regular">
                  Pesquisar{" "}
                  <em className="not-italic font-semibold">
                    &laquo;{query.trim()}&raquo;
                  </em>{" "}
                  nos/nas{" "}
                  <strong>{option.label}</strong>
                </span>
                <svg
                  className="w-16 h-16 text-neutral-400"
                  fill="none"
                  viewBox="0 0 24 24"
                  stroke="currentColor"
                  aria-hidden="true"
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth={2}
                    d="M9 5l7 7-7 7"
                  />
                </svg>
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}
