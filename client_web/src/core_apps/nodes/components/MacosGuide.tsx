import React from 'react';
import { GuideSteps } from './GuideSteps';
import { PreparationNotice } from './PreparationNotice';
import { ServerAddressBox } from './ServerAddressBox';

export const MacosGuide: React.FC = () => (
  <div className="flex flex-col gap-6">
    <PreparationNotice prefix="install_macos" />
    <GuideSteps prefix="install_macos" count={3} titleKey="install_macos_now_title" />
    <ServerAddressBox hintKey="install_macos_address_hint" />
  </div>
);
