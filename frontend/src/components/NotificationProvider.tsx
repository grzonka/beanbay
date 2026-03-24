import { API_ERROR_EVENT } from '@/api/client';
import { Alert, Snackbar, useMediaQuery, useTheme } from '@mui/material';
import {
  type ReactNode,
  createContext,
  useCallback,
  useContext,
  useEffect,
  useState,
} from 'react';

interface Notification {
  id: number;
  message: string;
  severity: 'success' | 'error' | 'warning' | 'info';
  autoHide?: number;
}

interface NotificationContextValue {
  notify: (
    message: string,
    severity?: Notification['severity'],
    autoHide?: number,
  ) => void;
}

const NotificationContext = createContext<NotificationContextValue>({
  notify: () => {},
});

export const useNotification = () => useContext(NotificationContext);

let nextId = 0;

export function NotificationProvider({ children }: { children: ReactNode }) {
  const [notifications, setNotifications] = useState<Notification[]>([]);
  const theme = useTheme();
  const isMobile = useMediaQuery(theme.breakpoints.down('sm'));

  const notify = useCallback(
    (
      message: string,
      severity: Notification['severity'] = 'success',
      autoHide = 3000,
    ) => {
      const id = nextId++;
      setNotifications((prev) => [
        ...prev,
        { id, message, severity, autoHide },
      ]);
    },
    [],
  );

  const handleClose = useCallback((id: number) => {
    setNotifications((prev) => prev.filter((n) => n.id !== id));
  }, []);

  useEffect(() => {
    const handler = (e: Event) => {
      const { message } = (e as CustomEvent).detail;
      notify(message, 'error', undefined);
    };
    window.addEventListener(API_ERROR_EVENT, handler);
    return () => window.removeEventListener(API_ERROR_EVENT, handler);
  }, [notify]);

  return (
    <NotificationContext.Provider value={{ notify }}>
      {children}
      {notifications.map((n) => (
        <Snackbar
          key={n.id}
          open
          autoHideDuration={
            n.severity === 'error' ? null : (n.autoHide ?? 3000)
          }
          onClose={() => handleClose(n.id)}
          anchorOrigin={{
            vertical: 'bottom',
            horizontal: isMobile ? 'center' : 'left',
          }}
        >
          <Alert
            severity={n.severity}
            onClose={() => handleClose(n.id)}
            variant="filled"
          >
            {n.message}
          </Alert>
        </Snackbar>
      ))}
    </NotificationContext.Provider>
  );
}
