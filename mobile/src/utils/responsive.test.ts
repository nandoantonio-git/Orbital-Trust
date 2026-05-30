// Type-level test for useResponsive hook
// This file serves as a compile-time contract test — tsc IS the test runner here.

import { useResponsive, type ResponsiveValues } from './responsive';

// Assert the hook signature is callable and returns the expected shape
declare const result: ReturnType<typeof useResponsive>;

const _isWeb: boolean = result.isWeb;
const _isTablet: boolean = result.isTablet;
const _maxWidth: number = result.maxWidth;

const _fontSizes: ResponsiveValues['fontSizes'] = result.fontSizes;
const _h1: number = result.fontSizes.h1;
const _h2: number = result.fontSizes.h2;
const _h3: number = result.fontSizes.h3;
const _body: number = result.fontSizes.body;
const _label: number = result.fontSizes.label;
const _caption: number = result.fontSizes.caption;

const _spacing: ResponsiveValues['spacing'] = result.spacing;
const _xs: number = result.spacing.xs;
const _sm: number = result.spacing.sm;
const _md: number = result.spacing.md;
const _lg: number = result.spacing.lg;

export {};
