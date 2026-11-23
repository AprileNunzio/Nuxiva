import React from 'react';
import { GuideSteps } from './GuideSteps';
import { PreparationNotice } from './PreparationNotice';
import { ServerAddressBox } from './ServerAddressBox';

export const IosGuide: React.FC = () => (
  <div className="flex flex-col gap-6">
    <PreparationNotice prefix="install_ios" />
    <GuideSteps prefix="install_ios" count={4} titleKey="install_ios_pairing_title" />
    <ServerAddressBox hintKey="install_ios_address_hint" />
  </div>
);
