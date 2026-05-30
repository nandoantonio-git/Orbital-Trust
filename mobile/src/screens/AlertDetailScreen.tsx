import React, { useEffect, useState } from 'react';
import {
  ActivityIndicator,
  Image,
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
import { useResponsive } from '../utils/responsive';

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
  const [imageError, setImageError] = useState(false);
  const { fontSizes, spacing } = useResponsive();

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
        <Text style={[styles.errorText, { fontSize: fontSizes.body }]}>Alerta não encontrado.</Text>
      </View>
    );
  }

  const formattedDate = new Date(alert.timestamp).toLocaleString('pt-BR');

  return (
    <ScrollView style={styles.container} contentContainerStyle={{ alignItems: 'center' }}>
      {alert.image_url && !imageError ? (
        <Image
          source={{ uri: alert.image_url }}
          style={styles.satelliteImage}
          resizeMode="contain"
          onError={() => setImageError(true)}
        />
      ) : (
        <View style={styles.imagePlaceholder}>
          <Text style={[styles.imagePlaceholderText, { fontSize: fontSizes.body }]}>Imagem não disponível</Text>
        </View>
      )}
      <View style={[styles.content, { padding: spacing.md, paddingBottom: spacing.lg }]}>
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
        <Text style={[styles.bodyText, { fontSize: fontSizes.body }]}>{alert.explanation}</Text>

        <SectionTitle title="Recomendação" />
        <Text style={[styles.bodyText, { fontSize: fontSizes.body }]}>{alert.recommendation}</Text>

        <Text style={[styles.footer, { fontSize: fontSizes.caption }]}>Modelo: {alert.model_version}</Text>
      </View>
    </ScrollView>
  );
}

function SectionTitle({ title }: { title: string }): JSX.Element {
  const { fontSizes } = useResponsive();
  return <Text style={[styles.sectionTitle, { fontSize: fontSizes.h3 }]}>{title}</Text>;
}

function DetailRow({ label, value }: { label: string; value: string }): JSX.Element {
  const { fontSizes } = useResponsive();
  return (
    <View style={styles.row}>
      <Text style={[styles.rowLabel, { fontSize: fontSizes.label }]}>{label}</Text>
      <Text style={[styles.rowValue, { fontSize: fontSizes.label }]}>{value}</Text>
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
    maxWidth: 600,
    alignSelf: 'center',
    width: '100%',
  },
  centered: {
    flex: 1,
    alignItems: 'center',
    justifyContent: 'center',
    backgroundColor: '#f5f5f5',
  },
  errorText: {
    color: '#888',
  },
  badgeRow: {
    flexDirection: 'row',
    gap: 8,
    marginBottom: 16,
  },
  row: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    justifyContent: 'space-between',
    paddingVertical: 10,
    borderBottomWidth: 1,
    borderBottomColor: '#e5e5e5',
  },
  rowLabel: {
    color: '#555',
    flex: 1,
    minWidth: 120,
  },
  rowValue: {
    color: '#1a1a2e',
    fontWeight: '500',
    flex: 1,
    minWidth: 120,
    textAlign: 'right',
  },
  sectionTitle: {
    fontWeight: '600',
    color: '#1a1a2e',
    marginTop: 20,
    marginBottom: 8,
  },
  bodyText: {
    color: '#333',
    lineHeight: 22,
  },
  footer: {
    color: '#aaa',
    marginTop: 24,
    textAlign: 'right',
  },
  satelliteImage: {
    width: '100%',
    aspectRatio: 1,
    maxWidth: 400,
    alignSelf: 'center',
  },
  imagePlaceholder: {
    width: '100%',
    aspectRatio: 1,
    maxWidth: 400,
    alignSelf: 'center',
    backgroundColor: '#e0e0e0',
    alignItems: 'center',
    justifyContent: 'center',
  },
  imagePlaceholderText: {
    color: '#888',
  },
});
