/// <reference types="vite/client" />

interface ImportMetaEnv {
  readonly VITE_QUERY_CACHE_TTL_MS?: string;
  readonly VITE_DISABLE_STRICT_MODE?: string;
}

interface ImportMeta {
  readonly env: ImportMetaEnv;
}

declare module 'react-plotly.js' {
  import { Component, type CSSProperties } from 'react';
  
  export interface PlotProps {
    data: unknown[];
    layout?: unknown;
    config?: unknown;
    style?: CSSProperties;
    className?: string;
    onInitialized?: (figure: unknown, graphDiv: HTMLElement) => void;
    onUpdate?: (figure: unknown, graphDiv: HTMLElement) => void;
    onError?: (err: Error) => void;
  }
  
  export default class Plot extends Component<PlotProps> {}
}
