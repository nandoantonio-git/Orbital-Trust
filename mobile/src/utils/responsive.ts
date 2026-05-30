import { useWindowDimensions, Platform } from 'react-native';

export interface ResponsiveValues {
  isWeb: boolean;
  isTablet: boolean;
  fontSizes: {
    h1: number;
    h2: number;
    h3: number;
    body: number;
    label: number;
    caption: number;
  };
  spacing: {
    xs: number;
    sm: number;
    md: number;
    lg: number;
  };
  maxWidth: number;
}

export function useResponsive(): ResponsiveValues {
  const { width } = useWindowDimensions();
  const wide = width > 600;

  return {
    isWeb: Platform.OS === 'web',
    isTablet: wide,
    fontSizes: wide
      ? { h1: 32, h2: 20, h3: 18, body: 16, label: 15, caption: 13 }
      : { h1: 26, h2: 18, h3: 16, body: 14, label: 13, caption: 12 },
    spacing: wide
      ? { xs: 8, sm: 16, md: 24, lg: 32 }
      : { xs: 4, sm: 8, md: 16, lg: 24 },
    maxWidth: 600,
  };
}
