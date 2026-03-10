import { AdminSidebar } from '@/components/admin/AdminSidebar';
import { AdminHeader } from '@/components/admin/AdminHeader';

export default function AdminLayout({
    children,
}: {
    children: React.ReactNode;
}) {
    return (
        <div className="flex flex-col min-h-screen bg-white">
            <div className="flex grow relative">
                <AdminSidebar />
                <div className="flex flex-col grow ml-[114px]">
                    <AdminHeader />
                    <main className="grow">
                        {children}
                    </main>
                </div>
            </div>
        </div>
    );
}
