/// <reference types="vite/client" />

declare module 'react-plotly.js' {
  import { Component } from 'react';
  import { PlotParams } from 'plotly.js';
  
  export interface PlotProps {
    data: any[];
    layout?: any;
    config?: any;
    style?: React.CSSProperties;
    className?: string;
    onInitialized?: (figure: any, graphDiv: HTMLElement) => void;
    onUpdate?: (figure: any, graphDiv: HTMLElement) => void;
    onError?: (err: Error) => void;
  }
  
  export default class Plot extends Component<PlotProps> {}
}
