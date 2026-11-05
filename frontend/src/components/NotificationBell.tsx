"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import { apiFetch, apiPost, orgPath } from "@/lib/api";

interface Item {
  id: string;
  title: string;
  body: string;
  link: string;
  read_at: string | null;
  created_at: string;
}

/** In-app notifications. While any tab is open, new ones also raise a desktop
 *  notification (if the user allowed it); emails cover the case of no open tab. */
export function NotificationBell({ org }: { org: string }) {
  const router = useRouter();
  const [inbox, setInbox] = useState<{ unread: number; results: Item[] }>({ unread: 0, results: [] });
  const [open, setOpen] = useState(false);
  const seen = useRef<Set<string> | null>(null);

  const load = useCallback(async () => {
    try {
      const data = await apiFetch(orgPath(org, "notifications/"));
      if (seen.current && typeof Notification !== "undefined" && Notification.permission === "granted") {
        for (const item of data.results as Item[]) {
          if (!item.read_at && !seen.current.has(item.id)) new Notification(item.title, { body: item.body });
        }
      }
      seen.current = new Set((data.results as Item[]).map((item) => item.id));
      setInbox(data);
    } catch {
      // Polling failures are transient; the next poll retries.
    }
  }, [org]);

  useEffect(() => {
    seen.current = null;
    load();
    const timer = setInterval(load, 20000);
    return () => clearInterval(timer);
  }, [load]);

  const openItem = async (item: Item) => {
    setOpen(false);
    if (!item.read_at) await apiPost(orgPath(org, `notifications/${item.id}/read/`), {});
    load();
    if (item.link) router.push(item.link);
  };

  return (
    <div className="relative">
      <button
        onClick={() => setOpen(!open)}
        className="relative p-1 text-gray-600 hover:text-gray-900"
        aria-label={`Notifications (${inbox.unread} unread)`}
      >
        <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
          <path d="M18 8a6 6 0 0 0-12 0c0 7-3 9-3 9h18s-3-2-3-9" />
          <path d="M13.73 21a2 2 0 0 1-3.46 0" />
        </svg>
        {inbox.unread > 0 && (
          <span className="absolute -top-1 -right-1 bg-red-600 text-white text-[10px] rounded-full min-w-4 h-4 px-1 flex items-center justify-center">
            {inbox.unread}
          </span>
        )}
      </button>
      {open && (
        <div className="absolute right-0 mt-2 w-80 bg-white border border-gray-200 rounded-lg shadow-lg z-10">
          <div className="flex items-center justify-between px-4 py-2 border-b border-gray-100">
            <span className="text-sm font-medium">Notifications</span>
            {inbox.unread > 0 && (
              <button
                onClick={async () => {
                  await apiPost(orgPath(org, "notifications/read-all/"), {});
                  load();
                }}
                className="text-xs text-blue-600 hover:underline"
              >
                Mark all read
              </button>
            )}
          </div>
          {inbox.results.length === 0 && <p className="px-4 py-6 text-sm text-gray-400 text-center">Nothing yet.</p>}
          <ul className="max-h-96 overflow-y-auto">
            {inbox.results.map((item) => (
              <li key={item.id}>
                <button
                  onClick={() => openItem(item)}
                  className={`w-full text-left px-4 py-3 border-b border-gray-50 hover:bg-gray-50 ${item.read_at ? "text-gray-500" : ""}`}
                >
                  <div className="text-sm font-medium flex items-center gap-2">
                    {!item.read_at && <span className="w-2 h-2 rounded-full bg-blue-500 shrink-0" />}
                    {item.title}
                  </div>
                  {item.body && <div className="text-xs text-gray-500 mt-0.5 line-clamp-2">{item.body}</div>}
                  <div className="text-xs text-gray-400 mt-1">{new Date(item.created_at).toLocaleString()}</div>
                </button>
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}
