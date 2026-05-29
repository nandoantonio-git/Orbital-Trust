import React, { useEffect, useState } from 'react';
import {
  ActivityIndicator,
  ScrollView,
  StyleSheet,
  Text,
  View,
} from 'react-native';
import { useRoute } from '@react-navigation/native';
import type { RouteProp } from '@react-navigation/native';
import ConfidenceBadge from '../components/ConfidenceBadge';
import RiskBadge from '../components/RiskBadge';
import { getAlertById } from '../services/alertService';
import { saveToHistory } from '../services/historyService';
import type { AlertResponse } from '../types/alert';
import type { RootStackParamList } from './DashboardScreen';

type AlertDetailRouteProp = RouteProp<RootStackParamList, 'AlertDetail'>;

const CLASS_LABELS: Record<string, string> = {
  queimada: 'Queimada',
  solo_exposto: 'Solo Exposto',
  vegetacao: 'Vegetação',
  agua: 'Água',
  baixa_visibilidade: 'Baixa Visibilidade',
};

export default function AlertDetailScreen(): JSX.Element {
  const route = useRoute<AlertDetailRouteProp>();
  const { alertId } = route.params;
  const [alert, setAlert] = useState<AlertResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [notFound, setNotFound] = useState(false);

  useEffect(() => {
    getAlertById(alertId)
      .then((data) => {
        if (data === null) {
          setNotFound(true);
        } else {
          setAlert(data);
          saveToHistory(data).catch(() => undefined);
        }
      })
      .finally(() => setLoading(false));
  }, [alertId]);

  if (loading) {
    return (
      <View style={styles.centered}>
        <ActivityIndicator size="large" color="#1a1a2e" />
      </View>
    );
  }

  if (notFound || alert === null) {
    return (
      <View style={styles.centered}>
        <Text style={styles.errorText}>Alerta não encontrado.</Text>
      </View>
    );
  }

  const formattedDate = new Date(alert.timestamp).toLocaleString('pt-BR');

  return (
    <ScrollView style={styles.container} contentContainerStyle={styles.content}>
      <View style={styles.badgeRow}>
        <RiskBadge riskLevel={alert.risk_level} />
        <ConfidenceBadge confidence={alert.analysis_confidence} />
      </View>

      <DetailRow
        label="Classe Detectada"
        value={CLASS_LABELS[alert.detected_class] ?? alert.detected_class}
      />
      {alert.class_percentage !== undefined && (
        <DetailRow
          label="Percentual da Área"
          value={`${alert.class_percentage.toFixed(1)}%`}
        />
      )}
      {alert.change_score !== undefined && (
        <DetailRow
          label="Change Score"
          value={alert.change_score.toFixed(2)}
        />
      )}
      {alert.source !== undefined && (
        <DetailRow label="Fonte" value={alert.source} />
      )}
      <DetailRow label="Data/Hora" value={formattedDate} />

      <SectionTitle title="Explicação" />
      <Text style={styles.bodyText}>{alert.explanation}</Text>

      <SectionTitle title="Recomendação" />
      <Text style={styles.bodyText}>{alert.recommendation}</Text>

      <Text style={styles.footer}>Modelo: {alert.model_version}</Text>
    </ScrollView>
  );
}

function SectionTitle({ title }: { title: string }): JSX.Element {
  return <Text style={styles.sectionTitle}>{title}</Text>;
}

function DetailRow({ label, value }: { label: string; value: string }): JSX.Element {
  return (
    <View style={styles.row}>
      <Text style={styles.rowLabel}>{label}</Text>
      <Text style={styles.rowValue}>{value}</Text>
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#f5f5f5',
  },
  content: {
    padding: 16,
    paddingBottom: 32,
  },
  centered: {
    flex: 1,
    alignItems: 'center',
    justifyContent: 'center',
    backgroundColor: '#f5f5f5',
  },
  errorText: {
    fontSize: 16,
    color: '#888',
  },
  badgeRow: {
    flexDirection: 'row',
    gap: 8,
    marginBottom: 16,
  },
  row: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    paddingVertical: 10,
    borderBottomWidth: 1,
    borderBottomColor: '#e5e5e5',
  },
  rowLabel: {
    fontSize: 14,
    color: '#555',
    flex: 1,
  },
  rowValue: {
    fontSize: 14,
    color: '#1a1a2e',
    fontWeight: '500',
    flex: 1,
    textAlign: 'right',
  },
  sectionTitle: {
    fontSize: 16,
    fontWeight: '600',
    color: '#1a1a2e',
    marginTop: 20,
    marginBottom: 8,
  },
  bodyText: {
    fontSize: 14,
    color: '#333',
    lineHeight: 22,
  },
  footer: {
    fontSize: 12,
    color: '#aaa',
    marginTop: 24,
    textAlign: 'right',
  },
});
