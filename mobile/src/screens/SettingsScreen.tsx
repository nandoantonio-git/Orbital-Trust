import React, { useEffect, useState } from 'react';
import {
  ActivityIndicator,
  ScrollView,
  StyleSheet,
  Text,
  TouchableOpacity,
  View,
} from 'react-native';
import { useNavigation } from '@react-navigation/native';
import type { StackNavigationProp } from '@react-navigation/stack';
import {
  checkAlertApiConnection,
  getAlertServiceSettings,
} from '../services/alertService';
import type {
  AlertServiceSettings,
  ConnectionStatus,
} from '../services/alertService';
import type { RootStackParamList } from './DashboardScreen';
import { useResponsive } from '../utils/responsive';

const MODE_LABEL: Record<AlertServiceSettings['mode'], string> = {
  mock: 'Mock',
  api: 'API',
};

const STATUS_LABEL: Record<ConnectionStatus, string> = {
  online: 'online',
  offline: 'offline',
  'não verificado': 'não verificado',
};

type SettingsNavProp = StackNavigationProp<RootStackParamList, 'Settings'>;

export default function SettingsScreen(): JSX.Element {
  const navigation = useNavigation<SettingsNavProp>();
  const settings = getAlertServiceSettings();
  const [connectionStatus, setConnectionStatus] = useState<ConnectionStatus>(
    settings.connectionStatus,
  );
  const [checking, setChecking] = useState(settings.mode === 'api');
  const { fontSizes, spacing } = useResponsive();

  useEffect(() => {
    let active = true;

    checkAlertApiConnection()
      .then((status) => {
        if (active) {
          setConnectionStatus(status);
        }
      })
      .finally(() => {
        if (active) {
          setChecking(false);
        }
      });

    return () => {
      active = false;
    };
  }, []);

  return (
    <ScrollView
      style={styles.container}
      contentContainerStyle={[
        styles.content,
        { padding: spacing.md, paddingBottom: spacing.lg },
      ]}
    >
      <View style={styles.header}>
        <Text style={[styles.title, { fontSize: fontSizes.h2 }]}>Configurações</Text>
        <Text style={[styles.subtitle, { fontSize: fontSizes.body }]}>
          Transparência de integração para a demonstração do MVP.
        </Text>
      </View>

      <View style={styles.card}>
        <Text style={[styles.sectionTitle, { fontSize: fontSizes.h3 }]}>Modo de dados</Text>
        <View style={styles.segmented}>
          <ModeSegment label="Mock" active={settings.mode === 'mock'} />
          <ModeSegment label="API" active={settings.mode === 'api'} />
        </View>
        <InfoRow label="Modo atual" value={MODE_LABEL[settings.mode]} />
        <Text style={[styles.helpText, { fontSize: fontSizes.caption }]}>
          O modo é fixo para o MVP e vem das variáveis públicas do Expo.
        </Text>
      </View>

      <View style={styles.card}>
        <Text style={[styles.sectionTitle, { fontSize: fontSizes.h3 }]}>Integração API</Text>
        {settings.mode === 'api' ? (
          <InfoRow label="Base URL" value={settings.baseUrl} />
        ) : (
          <InfoRow label="Base URL" value="API desativada no modo mock" />
        )}
        <View style={styles.statusRow}>
          <Text style={[styles.rowLabel, { fontSize: fontSizes.label }]}>Status</Text>
          <View style={styles.statusValue}>
            {checking && <ActivityIndicator size="small" color="#1a1a2e" />}
            <StatusPill status={connectionStatus} />
          </View>
        </View>
      </View>

      <TouchableOpacity
        activeOpacity={0.8}
        onPress={() => navigation.navigate('About')}
        style={styles.linkCard}
      >
        <View style={styles.linkTextGroup}>
          <Text style={[styles.sectionTitle, { fontSize: fontSizes.h3 }]}>Sobre</Text>
          <Text style={[styles.helpText, { fontSize: fontSizes.caption }]}>
            Propósito, funcionamento e transparência do Orbital Trust.
          </Text>
        </View>
        <Text style={[styles.linkArrow, { fontSize: fontSizes.h3 }]}>{'>'}</Text>
      </TouchableOpacity>
    </ScrollView>
  );
}

function ModeSegment({
  label,
  active,
}: {
  label: string;
  active: boolean;
}): JSX.Element {
  const { fontSizes } = useResponsive();

  return (
    <View style={[styles.segment, active && styles.segmentActive]}>
      <Text
        style={[
          styles.segmentText,
          active && styles.segmentTextActive,
          { fontSize: fontSizes.label },
        ]}
      >
        {label}
      </Text>
    </View>
  );
}

function InfoRow({ label, value }: { label: string; value: string }): JSX.Element {
  const { fontSizes } = useResponsive();

  return (
    <View style={styles.row}>
      <Text style={[styles.rowLabel, { fontSize: fontSizes.label }]}>{label}</Text>
      <Text style={[styles.rowValue, { fontSize: fontSizes.label }]}>{value}</Text>
    </View>
  );
}

function StatusPill({ status }: { status: ConnectionStatus }): JSX.Element {
  const { fontSizes } = useResponsive();
  const statusStyle =
    status === 'online'
      ? styles.statusOnline
      : status === 'offline'
        ? styles.statusOffline
        : styles.statusUnchecked;

  return (
    <View style={[styles.statusPill, statusStyle]}>
      <Text style={[styles.statusText, { fontSize: fontSizes.caption }]}>
        {STATUS_LABEL[status]}
      </Text>
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#f5f5f5',
  },
  content: {
    maxWidth: 600,
    alignSelf: 'center',
    width: '100%',
  },
  header: {
    marginBottom: 16,
  },
  title: {
    color: '#1a1a2e',
    fontWeight: '700',
    marginBottom: 6,
  },
  subtitle: {
    color: '#555',
    lineHeight: 22,
  },
  card: {
    backgroundColor: '#fff',
    borderRadius: 12,
    padding: 16,
    marginBottom: 12,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 1 },
    shadowOpacity: 0.08,
    shadowRadius: 4,
    elevation: 2,
  },
  linkCard: {
    alignItems: 'center',
    backgroundColor: '#fff',
    borderRadius: 12,
    elevation: 2,
    flexDirection: 'row',
    justifyContent: 'space-between',
    marginBottom: 12,
    minHeight: 72,
    padding: 16,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 1 },
    shadowOpacity: 0.08,
    shadowRadius: 4,
  },
  linkTextGroup: {
    flex: 1,
    paddingRight: 12,
  },
  linkArrow: {
    color: '#1a1a2e',
    fontWeight: '600',
  },
  sectionTitle: {
    color: '#1a1a2e',
    fontWeight: '600',
    marginBottom: 12,
  },
  segmented: {
    flexDirection: 'row',
    backgroundColor: '#eef0f4',
    borderRadius: 8,
    padding: 4,
    marginBottom: 14,
  },
  segment: {
    flex: 1,
    minHeight: 40,
    alignItems: 'center',
    justifyContent: 'center',
    borderRadius: 6,
  },
  segmentActive: {
    backgroundColor: '#1a1a2e',
  },
  segmentText: {
    color: '#555',
    fontWeight: '600',
  },
  segmentTextActive: {
    color: '#fff',
  },
  row: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    justifyContent: 'space-between',
    paddingVertical: 10,
    borderTopWidth: 1,
    borderTopColor: '#e5e5e5',
  },
  rowLabel: {
    color: '#555',
    flex: 1,
    minWidth: 120,
  },
  rowValue: {
    color: '#1a1a2e',
    flex: 1,
    fontWeight: '500',
    minWidth: 180,
    textAlign: 'right',
  },
  helpText: {
    color: '#777',
    lineHeight: 18,
    marginTop: 4,
  },
  statusRow: {
    alignItems: 'center',
    borderTopWidth: 1,
    borderTopColor: '#e5e5e5',
    flexDirection: 'row',
    flexWrap: 'wrap',
    justifyContent: 'space-between',
    paddingVertical: 10,
  },
  statusValue: {
    alignItems: 'center',
    flexDirection: 'row',
    gap: 8,
  },
  statusPill: {
    borderRadius: 999,
    paddingHorizontal: 10,
    paddingVertical: 4,
  },
  statusOnline: {
    backgroundColor: '#e7f6ed',
  },
  statusOffline: {
    backgroundColor: '#fdebec',
  },
  statusUnchecked: {
    backgroundColor: '#fff4d6',
  },
  statusText: {
    color: '#1a1a2e',
    fontWeight: '600',
  },
});
