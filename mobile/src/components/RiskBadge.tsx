import React from 'react';
import { StyleSheet, Text, View } from 'react-native';
import { RiskLevel } from '../types/alert';
import { useResponsive } from '../utils/responsive';

interface Props {
  riskLevel: RiskLevel;
}

const RISK_CONFIG: Record<RiskLevel, { color: string; label: string }> = {
  baixo: { color: '#22c55e', label: 'BAIXO' },
  medio: { color: '#eab308', label: 'MÉDIO' },
  alto: { color: '#ef4444', label: 'ALTO' },
};

export default function RiskBadge({ riskLevel }: Props): JSX.Element {
  const { color, label } = RISK_CONFIG[riskLevel];
  const { fontSizes } = useResponsive();

  return (
    <View style={[styles.badge, { backgroundColor: color }]}>
      <Text style={[styles.text, { fontSize: fontSizes.caption }]}>{label}</Text>
    </View>
  );
}

const styles = StyleSheet.create({
  badge: {
    paddingHorizontal: 10,
    paddingVertical: 4,
    borderRadius: 12,
    alignSelf: 'flex-start',
  },
  text: {
    color: '#fff',
    fontWeight: '600',
  },
});
