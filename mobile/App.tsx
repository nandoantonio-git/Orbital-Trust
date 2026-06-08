import React from 'react';
import { StyleSheet, Text, TouchableOpacity, View } from 'react-native';
import { NavigationContainer } from '@react-navigation/native';
import type { LinkingOptions } from '@react-navigation/native';
import { createStackNavigator } from '@react-navigation/stack';
import DashboardScreen from './src/screens/DashboardScreen';
import AlertDetailScreen from './src/screens/AlertDetailScreen';
import HistoryScreen from './src/screens/HistoryScreen';
import SettingsScreen from './src/screens/SettingsScreen';
import AboutScreen from './src/screens/AboutScreen';
import type { RootStackParamList } from './src/screens/DashboardScreen';

const Stack = createStackNavigator<RootStackParamList>();

const linking: LinkingOptions<RootStackParamList> = {
  prefixes: [], // prefixes not used on web
  config: {
    screens: {
      Dashboard: '',
      AlertDetail: 'alerts/:alertId',
      History: 'history',
      Settings: 'settings',
      About: 'about',
    },
  },
};

export default function App(): JSX.Element {
  return (
    <NavigationContainer linking={linking}>
      <Stack.Navigator initialRouteName="Dashboard">
        <Stack.Screen
          name="Dashboard"
          component={DashboardScreen}
          options={({ navigation }) => ({
            title: 'Orbital Trust',
            headerRight: () => (
              <View style={styles.headerActions}>
                <TouchableOpacity
                  onPress={() => navigation.navigate('About')}
                  style={styles.headerButton}
                >
                  <Text style={styles.headerButtonText}>Sobre</Text>
                </TouchableOpacity>
                <TouchableOpacity
                  onPress={() => navigation.navigate('History')}
                  style={styles.headerButton}
                >
                  <Text style={styles.headerButtonText}>Histórico</Text>
                </TouchableOpacity>
                <TouchableOpacity
                  onPress={() => navigation.navigate('Settings')}
                  style={styles.headerButton}
                >
                  <Text style={styles.headerButtonText}>Config</Text>
                </TouchableOpacity>
              </View>
            ),
          })}
        />
        <Stack.Screen
          name="AlertDetail"
          component={AlertDetailScreen}
          options={{ title: 'Detalhe do Alerta' }}
        />
        <Stack.Screen
          name="History"
          component={HistoryScreen}
          options={{ title: 'Histórico' }}
        />
        <Stack.Screen
          name="Settings"
          component={SettingsScreen}
          options={{ title: 'Configurações' }}
        />
        <Stack.Screen
          name="About"
          component={AboutScreen}
          options={{ title: 'Orbital Trust' }}
        />
      </Stack.Navigator>
    </NavigationContainer>
  );
}

const styles = StyleSheet.create({
  headerActions: {
    flexDirection: 'row',
    marginRight: 8,
  },
  headerButton: {
    justifyContent: 'center',
    minHeight: 44,
    paddingHorizontal: 8,
    paddingVertical: 8,
  },
  headerButtonText: {
    color: '#1a1a2e',
    fontSize: 14,
  },
});
