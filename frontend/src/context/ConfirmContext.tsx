import { createContext, useContext, useState, useCallback, type ReactNode } from 'react';
import './Confirm.css';

interface ConfirmState {
  message: string;
  title?: string;
  resolve: (value: boolean) => void;
}

interface ConfirmContextValue {
  confirm: (message: string, title?: string) => Promise<boolean>;
}

const ConfirmContext = createContext<ConfirmContextValue>({
  confirm: () => Promise.resolve(false),
});

export const ConfirmProvider = ({ children }: { children: ReactNode }) => {
  const [state, setState] = useState<ConfirmState | null>(null);

  const confirm = useCallback((message: string, title?: string): Promise<boolean> => {
    return new Promise<boolean>(resolve => setState({ message, title, resolve }));
  }, []);

  const handle = (value: boolean) => {
    state?.resolve(value);
    setState(null);
  };

  return (
    <ConfirmContext.Provider value={{ confirm }}>
      {children}
      {state && (
        <div className="confirm-overlay" onClick={() => handle(false)}>
          <div className="confirm-modal serpent-card" onClick={e => e.stopPropagation()}>
            {state.title && <h3 className="confirm-title">{state.title}</h3>}
            <p className="confirm-message">{state.message}</p>
            <div className="confirm-actions">
              <button className="confirm-btn cancel" onClick={() => handle(false)}>
                Отмена
              </button>
              <button className="confirm-btn ok" onClick={() => handle(true)}>
                Подтвердить
              </button>
            </div>
          </div>
        </div>
      )}
    </ConfirmContext.Provider>
  );
};

export const useConfirm = () => useContext(ConfirmContext);
