import { Component, type ErrorInfo, type ReactNode } from 'react';

interface Props {
  children: ReactNode;
}

interface State {
  hasError: boolean;
  error: Error | null;
  errorInfo: ErrorInfo | null;
}

class ErrorBoundary extends Component<Props, State> {
  constructor(props: Props) {
    super(props);
    this.state = { hasError: false, error: null, errorInfo: null };
  }

  static getDerivedStateFromError(error: Error): Partial<State> {
    return { hasError: true, error };
  }

  componentDidCatch(error: Error, errorInfo: ErrorInfo) {
    this.setState({ errorInfo });
    console.error('ErrorBoundary caught:', error, errorInfo);
  }

  handleReload = () => {
    window.location.reload();
  };

  handleGoHome = () => {
    window.location.href = '/';
  };

  render() {
    if (this.state.hasError) {
      const isDev = import.meta.env.DEV;

      return (
        <div className="min-h-screen flex items-center justify-center bg-[var(--color-dark-900)] p-6">
          <div className="max-w-lg w-full bg-[var(--surface-raised)] border border-[var(--surface-border)] rounded-xl shadow-lg p-8 text-center">
            <div className="text-4xl mb-4">⚠</div>
            <h1 className="text-xl font-serif font-bold text-[var(--color-dark-300)] mb-2">
              Bir hata olustu
            </h1>
            <p className="text-[var(--color-dark-400)] text-sm mb-6">
              Beklenmeyen bir sorun nedeniyle bu sayfa goruntulenemiyor.
            </p>

            <div className="flex gap-3 justify-center mb-6">
              <button
                onClick={this.handleReload}
                className="px-4 py-2 rounded-lg bg-[var(--color-accent-primary)] text-white dark:text-[#0F1A17] font-medium text-sm hover:opacity-90 transition-opacity"
              >
                Sayfayi Yenile
              </button>
              <button
                onClick={this.handleGoHome}
                className="px-4 py-2 rounded-lg border border-[var(--surface-border-strong)] text-[var(--color-dark-400)] font-medium text-sm hover:bg-[var(--color-dark-800)] transition-colors"
              >
                Ana Sayfaya Don
              </button>
            </div>

            {isDev && this.state.error && (
              <details className="text-left mt-4 border-t border-[var(--surface-border)] pt-4">
                <summary className="text-xs text-[var(--color-dark-400)] cursor-pointer hover:text-[var(--color-dark-300)]">
                  Teknik Detaylar (Development)
                </summary>
                <pre className="mt-2 p-3 bg-[var(--color-dark-900)] rounded-lg text-xs text-red-400 overflow-auto max-h-48 font-mono">
                  {this.state.error.toString()}
                  {this.state.errorInfo?.componentStack}
                </pre>
              </details>
            )}
          </div>
        </div>
      );
    }

    return this.props.children;
  }
}

export default ErrorBoundary;
