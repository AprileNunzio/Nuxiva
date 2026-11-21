import React, { useEffect, useState } from 'react';
import { useScopedI18n } from '../../shared/i18n/useScopedI18n';
import { RemoteKioskAdvisoryModal } from './RemoteKioskAdvisoryModal';
import {
  saveRemoteKioskAdvisoryAck,
  shouldShowRemoteKioskAdvisory,
  syncRemoteKioskBackend,
} from './remoteKioskStorage';

export const RemoteKioskGlobalPrompt: React.FC = () => {
  const { t } = useScopedI18n('features/remote_kiosk');
  const [isOpen, setIsOpen] = useState(false);

  useEffect(() => {
    if (shouldShowRemoteKioskAdvisory()) {
      setIsOpen(true);
    }
  }, []);

  const handleDecision = async (enable: boolean) => {
    saveRemoteKioskAdvisoryAck(enable);
    await syncRemoteKioskBackend(enable);
    setIsOpen(false);
  };

  if (!isOpen) return null;

  return (
    <RemoteKioskAdvisoryModal
      isOpen={isOpen}
      mandatory={true}
      onDecision={handleDecision}
      t={t}
    />
  );
};
