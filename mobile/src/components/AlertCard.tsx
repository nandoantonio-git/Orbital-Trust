import React from 'react';
import { StyleSheet, Text, TouchableOpacity, View } from 'react-native';
import { AlertResponse } from '../types/alert';
import { formatVisualEvidenceSummary } from '../utils/alertMetrics';
import { useResponsive } from '../utils/responsive';
import ConfidenceBadge from './ConfidenceBadge';
import RiskBadge from './RiskBadge';

interface Props {
  alert: AlertResponse;
  onPress: () => void;
}

const CLASS_LABEL: Record<AlertResponse['detected_class'], string> = {
  vegetacao: 'Vegetação',
  solo_exposto: 'Solo Exposto',
  agua: 'Água',
  queimada: 'Queimada',
  baixa_visibilidade: 'Baixa Visibilidade',
};

function formatTimestamp(iso: string): string {
  const date = new Date(iso);
  return date.toLocaleString('pt-BR', {
    day: '2-digit',
    month: '2-digit',
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  });
}

export default function AlertCard({ alert, onPress }: Props): JSX.Element {
  const { fontSizes } = useResponsive();
  return (
    <TouchableOpacity style={styles.card} onPress={onPress} activeOpacity={0.7}>
      <View style={styles.header}>
        <Text style={[styles.detectedClass, { fontSize: fontSizes.label }]}>
          {CLASS_LABEL[alert.detected_class]}
        </Text>
        <Text style={[styles.timestamp, { fontSize: fontSizes.caption }]}>{formatTimestamp(alert.timestamp)}</Text>
      </View>
      <View style={styles.badges}>
        <RiskBadge riskLevel={alert.risk_level} />
        <ConfidenceBadge confidence={alert.analysis_confidence} />
      </View>
      <Text style={[styles.evidenceSummary, { fontSize: fontSizes.caption }]}>
        {formatVisualEvidenceSummary(alert)}
      </Text>
    </TouchableOpacity>
  );
}

const styles = StyleSheet.create({
  card: {
    backgroundColor: '#fff',
    borderRadius: 12,
    padding: 16,
    minHeight: 80,
    marginHorizontal: 16,
    marginVertical: 6,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 1 },
    shadowOpacity: 0.08,
    shadowRadius: 4,
    elevation: 2,
    maxWidth: 600,
    alignSelf: 'center',
    width: '100%',
  },
  header: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: 10,
  },
  detectedClass: {
    fontWeight: '600',
    color: '#1a1a2e',
  },
  timestamp: {
    color: '#888',
  },
  badges: {
    flexDirection: 'row',
    gap: 8,
    marginBottom: 8,
  },
  evidenceSummary: {
    color: '#555',
    lineHeight: 18,
  },
});
