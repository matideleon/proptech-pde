"use client";

import { useState } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  LayoutDashboard,
  Building2,
  Map,
  BarChart3,
  Users,
  Bell,
  Settings,
  Search,
  ChevronLeft,
  Activity,
  Bot,
  Database,
  MessagesSquare,
  Menu,
  X,
} from "lucide-react";
import { cn } from "@/lib/utils";

const NAV_ITEMS = [
  {
    label: "Dashboard",
    href: "/dashboard",
    icon: LayoutDashboard,
  },
  {
    label: "Propiedades",
    href: "/properties",
    icon: Building2,
  },
  {
    label: "Mapa",
    href: "/dashboard/map",
    icon: Map,
  },
  {
    label: "Analytics",
    href: "/dashboard/analytics",
    icon: BarChart3,
  },
  {
    label: "CRM / Leads",
    href: "/crm",
    icon: Users,
  },
  {
    label: "Grupos FB",
    href: "/group-posts",
    icon: MessagesSquare,
  },
  {
    label: "Alertas",
    href: "/dashboard/alerts",
    icon: Bell,
  },
  {
    label: "Motor IA",
    href: "/dashboard/ai",
    icon: Bot,
  },
  {
    label: "Scraping",
    href: "/admin/scraping",
    icon: Database,
    admin: true,
  },
  {
    label: "Configuración",
    href: "/admin/settings",
    icon: Settings,
    admin: true,
  },
];

interface DashboardLayoutProps {
  children: React.ReactNode;
}

export function DashboardLayout({ children }: DashboardLayoutProps) {
  const [collapsed, setCollapsed] = useState(false);
  const [mobileOpen, setMobileOpen] = useState(false);
  const pathname = usePathname();

  const Sidebar = ({ mobile = false }: { mobile?: boolean }) => (
    <aside
      className={cn(
        "flex flex-col bg-card border-r transition-all duration-300",
        mobile ? "w-72 h-full" : collapsed ? "w-16" : "w-64",
        !mobile && "hidden lg:flex"
      )}
    >
      {/* Logo */}
      <div className={cn("flex items-center h-14 border-b px-4", collapsed && !mobile ? "justify-center" : "gap-3")}>
        <div className="w-7 h-7 rounded-lg bg-brand-500 flex items-center justify-center flex-shrink-0">
          <Building2 className="h-4 w-4 text-white" />
        </div>
        {(!collapsed || mobile) && (
          <div>
            <span className="font-bold text-sm text-foreground">PropTech</span>
            <span className="text-xs text-muted-foreground block -mt-0.5">Punta del Este</span>
          </div>
        )}
      </div>

      {/* Search */}
      {(!collapsed || mobile) && (
        <div className="px-3 py-3 border-b">
          <div className="flex items-center gap-2 bg-muted rounded-lg px-3 py-2">
            <Search className="h-3.5 w-3.5 text-muted-foreground" />
            <input
              placeholder="Buscar..."
              className="bg-transparent text-xs flex-1 outline-none text-foreground placeholder:text-muted-foreground"
            />
          </div>
        </div>
      )}

      {/* Navigation */}
      <nav className="flex-1 overflow-y-auto py-3 px-2">
        {NAV_ITEMS.map((item) => {
          const Icon = item.icon;
          const isActive = pathname === item.href || pathname.startsWith(item.href + "/");

          if (item.admin) {
            // Separador antes de sección admin
            if (item.label === "Scraping") {
              return (
                <div key="admin-separator">
                  {(!collapsed || mobile) && (
                    <div className="px-2 py-2 mt-2">
                      <p className="text-[10px] font-semibold text-muted-foreground uppercase tracking-wider">
                        Admin
                      </p>
                    </div>
                  )}
                  <NavItem item={item} isActive={isActive} collapsed={collapsed && !mobile} />
                </div>
              );
            }
          }

          return (
            <NavItem key={item.href} item={item} isActive={isActive} collapsed={collapsed && !mobile} />
          );
        })}
      </nav>

      {/* Footer */}
      <div className="border-t p-3">
        {(!collapsed || mobile) ? (
          <div className="flex items-center gap-3 px-2">
            <div className="w-8 h-8 rounded-full bg-brand-500 text-white text-xs font-bold flex items-center justify-center">
              A
            </div>
            <div className="flex-1 min-w-0">
              <p className="text-xs font-medium truncate">Admin User</p>
              <p className="text-xs text-muted-foreground truncate">admin@proptech.uy</p>
            </div>
          </div>
        ) : (
          <div className="flex justify-center">
            <div className="w-8 h-8 rounded-full bg-brand-500 text-white text-xs font-bold flex items-center justify-center">
              A
            </div>
          </div>
        )}
      </div>
    </aside>
  );

  return (
    <div className="flex h-screen bg-background overflow-hidden">
      {/* Desktop Sidebar */}
      <Sidebar />

      {/* Mobile overlay */}
      {mobileOpen && (
        <div className="fixed inset-0 z-50 lg:hidden">
          <div className="absolute inset-0 bg-black/50" onClick={() => setMobileOpen(false)} />
          <div className="absolute left-0 top-0 bottom-0">
            <Sidebar mobile />
          </div>
        </div>
      )}

      {/* Main content */}
      <div className="flex-1 flex flex-col min-w-0 overflow-hidden">
        {/* Top bar */}
        <header className="h-14 border-b bg-card flex items-center px-4 gap-3 flex-shrink-0">
          {/* Mobile menu */}
          <button
            className="lg:hidden"
            onClick={() => setMobileOpen(true)}
          >
            <Menu className="h-5 w-5" />
          </button>

          {/* Collapse toggle (desktop) */}
          <button
            className="hidden lg:flex items-center justify-center w-7 h-7 rounded-lg hover:bg-muted transition-colors"
            onClick={() => setCollapsed(!collapsed)}
          >
            <ChevronLeft
              className={cn(
                "h-4 w-4 transition-transform text-muted-foreground",
                collapsed && "rotate-180"
              )}
            />
          </button>

          <div className="flex-1" />

          {/* Actions */}
          <div className="flex items-center gap-2">
            <div className="flex items-center gap-1.5 text-xs text-muted-foreground bg-muted px-2.5 py-1.5 rounded-full">
              <Activity className="h-3 w-3 text-green-500" />
              <span>Sistema activo</span>
            </div>
            <button className="relative w-8 h-8 rounded-lg hover:bg-muted flex items-center justify-center">
              <Bell className="h-4 w-4 text-muted-foreground" />
              <span className="absolute top-1 right-1 w-2 h-2 bg-red-500 rounded-full" />
            </button>
          </div>
        </header>

        {/* Page content */}
        <main className="flex-1 overflow-y-auto p-6">
          {children}
        </main>
      </div>
    </div>
  );
}

function NavItem({
  item,
  isActive,
  collapsed,
}: {
  item: (typeof NAV_ITEMS)[0];
  isActive: boolean;
  collapsed: boolean;
}) {
  const Icon = item.icon;

  return (
    <Link
      href={item.href}
      className={cn(
        "flex items-center gap-3 px-3 py-2 rounded-lg text-sm transition-colors mb-0.5",
        isActive
          ? "bg-brand-50 text-brand-600 font-medium dark:bg-brand-950 dark:text-brand-400"
          : "text-muted-foreground hover:bg-muted hover:text-foreground",
        collapsed && "justify-center"
      )}
      title={collapsed ? item.label : undefined}
    >
      <Icon className="h-4 w-4 flex-shrink-0" />
      {!collapsed && <span>{item.label}</span>}
    </Link>
  );
}
