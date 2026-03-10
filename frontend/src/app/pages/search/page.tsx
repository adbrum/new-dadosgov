import { Suspense } from "react";
import SearchClient from "@/components/search/SearchClient";

export default function SearchPage() {
  return (
    <main className="flex-grow bg-white">
      <Suspense
        fallback={
          <div className="container mx-auto px-4 py-48 text-center text-neutral-500">
            A carregar pesquisa...
          </div>
        }
      >
        <SearchClient />
      </Suspense>
    </main>
  );
}
