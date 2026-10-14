# NUXIVA - Neural Unified eXperience for Interactive Vision & Automation

[🇬🇧 English](README.md) | [🇮🇹 Italiano](README_IT.md) | [🇫🇷 Français](README_FR.md)

## 🚀 Nouveautés de la Version 4.1.53 (Neuro-Core 5.0, Omni-Cortical Engine 6.5 & Architecture Dynamique Universelle)

Nuxiva introduit un saut générationnel dans les systèmes d'exploitation pour l'intelligence artificielle distribuée, associant architectures neuro-cognitives biologiques, calcul natif haute performance en Rust, auto-découverte dynamique universelle et autonomie spatiale zéro-trust :

- **Omni-Cortical Engine 6.5 & 6 Moteurs de Raisonnement Modulaires** : Découplage architectural complet suivant l'Open/Closed Principle avec détection dynamique via `EngineScanner`. Intègre six moteurs cognitifs distincts :
  1. `nuxiva-4.2-legacy` : *Legacy Chain-Sync* (pipeline séquentiel à jetons avec bascule en série, SLA 2500ms).
  2. `nuxiva-5.0-veloce` : *Veloce Synapse-Flash* (Ternary 1.58-bit avec Liquid LNN et bus spiking zéro-copie, SLA 25ms).
  3. `nuxiva-5.0-empatico` : *Empatico Synapse-Limbic* (Global Workspace à 8 voies parallèles avec fusion biométrique à 10Hz, SLA 120ms).
  4. `nuxiva-6.0-pro` : *Pro Omni-Latent* (Espace Latent Continu JEPA/Coconut avec plasticité TTT en direct dans la VRAM, SLA 15ms).
  5. `nuxiva-6.5-ultra` : *Ultra DeepThink-MCTS* (MCTS latent à 64 branches avec Process Reward Model dopaminergique, SLA 650ms).
  6. `nuxiva-6.5-auto` (Par défaut) : *Auto Thalamic-Adaptive* (Méta-orchestrateur thalamique basé sur le principe d'énergie libre $\psi$ et la charge matérielle, SLA 45ms).
- **Dynamique Neurale Spiking LIF & Plasticité Hebbienne STDP** : Cœur Spiking Neural Network (`native/crates/bus-core/src/spike.rs` et `installer_wizard/features/brain/components.py`) modélisant l'intégration et la fuite du potentiel de membrane ($\tau_m$), des périodes réfractaires dynamiques, des seuils de décharge modulés par le système limbique et une plasticité synaptique Hebbienne STDP ($A^+$, $A^-$, $\tau_{\text{stdp}}$) modulée par la dopamine.
- **Modulateur Limbique à 7 Axes et Liaison Sensorielle en Temps Réel** : Vecteur émotionnel continu à 7 dimensions (Valence, Éveil/Arousal, Dominance, Dopamine, Noradrénaline, Sérotonine, Cortisol). Liaison sensorielle temps réel intégrant le stress acoustique vocal (Ear/Voiceprint), la pression ambiante et la valence faciale (Scene/Fusion), et la présence biométrique (People/Presence), publiant des événements `biometrics.*` sur le bus `nuxiva_bus`. Le cortisol restreint le budget d'exploration en cas d'urgence, tandis que la dopamine stimule la curiosité.
- **Global Neuronal Workspace (GNW) et Inhibition Latérale GABAergique** : Raisonnement parallèle spéculatif multi-branches dans `brain_chain.py`. Dès qu'une hypothèse cognitive atteint le seuil d'allumage (ignition threshold), elle déclenche une inhibition latérale GABAergique instantanée annulant les branches concurrentes plus lentes en microsecondes. Intègre une recherche arborescente Monte Carlo (MCTS) évaluée par le critique prédictif du Jumeau Numérique (`predict_user_impact`).
- **Default Mode Network (DMN) et Consolidation Synaptique Nocturne du Sommeil REM** :
  - *Default Mode Network (`backend/loops.py`)* : Cycle de réflexion autonome en arrière-plan activé après 10 minutes d'inactivité de l'utilisateur pour consolider les mémoires à long terme et formuler des prédictions proactives (foresight). Toute interaction par chat réinitialise instantanément le minuteur.
  - *Consolidation Synaptique Nocturne (`vision/nightly.py` et `soup/trainer.py`)* : Cycle REM appliquant une décroissance, un élagage (pruning) et une stabilisation contrôlée des poids synaptiques STDP diurnes dans `brain/assignments.py`, contrecarrant la courbe de l'oubli d'Ebbinghaus.
- **Scanner Dynamique Universel avec Moteur Natif Rust (`bus-core`)** :
  - `FastScanner` natif en Rust exposé via PyO3 avec hachage ultra-rapide FNV-1a, parcours parallèle des dossiers et détection instantanée des changements par empreinte de métadonnées.
  - `UniversalScanner` générique avec validation de sécurité Zero-Trust de l'arbre syntaxique (AST) pour intercepter les imports et appels dangereux avant chargement, couplé à un `DirectoryWatcher` événementiel pour le rechargement à chaud.
  - Découverte automatique des routes API (`FeatureRouteScanner`) montant dynamiquement les routeurs FastAPI de toutes les fonctionnalités.
- **Widgets Dynamiques Modulaires et Deck Web Réactif** :
  - Architecture à répertoires dédiés pour tous les widgets (`server/web/widgets/<widget_id>/`) avec `manifest.json`, `widget.py` (dérivant de `BaseWidget`), contrôleur REST et WebSocket (`/widgets`, `/widgets/{id}/state`, `/widgets/{id}/action`, `/widgets/ws`).
  - Widgets dynamiques intégrés : `brain_activity` (activité neurale et vecteur limbique en direct), `cad_viewer` (visualiseur interactif DXF 2D/3D), `quick_actions` (déclencheurs rapides), `smart_switch` (relais domotiques), `system_status` (télémétrie matérielle), `weather` (capteurs météo).
  - Deck réactif React 18 (`client_web/src/features/dynamic_widgets/DynamicWidgetDeck.tsx`) avec flux WebSocket en temps réel.
- **Outils d'Agent Modulaires Dynamiques et ToolScanner** :
  - Architecture à répertoires dédiés (`server/features/agent_tools/<tool_id>/`) avec `BaseAgentTool`, `tool.py` et `manifest.json`.
  - Outils intégrés : `cad`, `generator_3d`, `google_suite` (Gmail, Calendar, Drive, Sheets, Docs), `image`, `maps`, `music`, `social` (Instagram, Facebook, X), `web_scraper`, `web_search`.
- **CEO Multi-Agent Orchestrator et AgentScanner Dynamique** :
  - Le CEO Orchestrator (`installer_wizard/features/team/ceo.py`) dirige chaque tour de conversation.
  - Propulsé par `AgentScanner` (`installer_wizard/features/team/scanner.py`) : aucune liste codée en dur dans le code ! Analyse dynamiquement au démarrage et en direct les dossiers `/features` et `/widgets`, indexant les tokens sémantiques, outils et capacités pour élaborer des plans de délégation (`ceo_delegate`, `ceo_overview`).
- **Triage Clinique Cognitif Tri-Agent et Surveillance Multimodale** :
  - Triage clinique cognitif à trois agents (`server/features/cognitive_triage_agents/`) avec agent médical, agent psychologique et verrou de sécurité déterministe (`triage_safety_interlock`).
  - Surveillance multimodale continue, Affective Fusion Engine, Hub pour Capteurs Portables (`WearableVitalsHub`) et détection de présence d'urgence.
  - Améliorateur audio avec solution de secours en pur Python pour les environnements sans NumPy.
- **File d'Attente des Installations en Arrière-Plan avec Vitesse et Tri par Taille (Go)** :
  - Affichage en temps réel de la vitesse de téléchargement (en Mo/s ou Ko/s), barre de progression et pourcentage pour chaque composant dans `bgqueue.js/css` et les panneaux d'administration.
  - Exécution ordonnée de la file strictement du plus petit composant en Go au plus volumineux, optimisant la bande passante et l'espace disque.
- **Mise à Niveau Forcée d'Urgence via SSH (`nuxivactl update --force`)** :
  - Script dédié `scripts/os/force-upgrade.sh` accessible via `sudo nuxivactl update --force` ou `sudo nuxiva-upgrade` pour réinitialiser brutalement le dépôt Git sur `origin/main`, purger les verrous obsolètes, synchroniser les dépendances, recompiler les crates Rust et redémarrer les services même si l'interface web est figée.
- **Configuration Initiale d'Éveil Modulaire et Non Bloquante** :
  - La procédure d'accueil et d'éveil a été transformée en un assistant de configuration initial optionnel, pouvant être ignoré ou réexécuté à tout moment sans bloquer l'écran kiosque ou le panneau d'administration.
- **Assainissement Système et Résolution du Quoting Récursif** :
  - Élimination du bogue de guillemets récursifs dans `/etc/nuxiva/nuxiva.env`, sécurisation des permissions d'Ollama et démarrage différé des services non configurés.
- **Écosystème Étendu** : 72 fonctionnalités système auto-détectées dans `installer_wizard/features/`, plus de 1 200 tests automatisés validés sous Rust, Python et TypeScript.

<p align="center">
  <img src="https://img.shields.io/badge/Architecture-Clean%20Architecture-00f0ff?style=for-the-badge" alt="Clean Architecture">
  <img src="https://img.shields.io/badge/Cognitif-Omni%20Cortical%206.5-purple?style=for-the-badge" alt="Omni-Cortical">
  <img src="https://img.shields.io/badge/Sécurité-Zero%20Trust%20Wasm-red?style=for-the-badge" alt="Zero Trust">
  <img src="https://img.shields.io/badge/Résilience-eBPF%20Self%20Healing-blue?style=for-the-badge" alt="eBPF">
  <img src="https://img.shields.io/badge/État-Event%20Sourcing-emerald?style=for-the-badge" alt="Event Sourcing">
  <img src="https://img.shields.io/badge/Calcul-P2P%20Mesh%20Swarm-amber?style=for-the-badge" alt="Swarm Compute">
  <a href="https://www.paypal.com/paypalme/NunzioAprile"><img src="https://img.shields.io/badge/Don-PayPal-00457C?style=for-the-badge&logo=paypal&logoColor=white" alt="PayPal"></a>
</p>

```text
 ███╗   ██╗██╗   ██╗██╗  ██╗██╗██╗   ██╗ █████╗ 
 ████╗  ██║██║   ██║╚██╗██╔╝██║██║   ██║██╔══██╗
 ██╔██╗ ██║██║   ██║ ╚███╔╝ ██║██║   ██║███████║
 ██║╚██╗██║██║   ██║ ██╔██╗ ██║╚██╗ ██╔╝██╔══██║
 ██║ ╚████║╚██████╔╝██╔╝ ██╗██║ ╚████╔╝ ██║  ██║
 ╚═╝  ╚═══╝ ╚═════╝ ╚═╝  ╚═╝╚═╝  ╚═══╝  ╚═╝  ╚═╝
 SYSTÈME D'EXPLOITATION IA DISTRIBUÉ - ENTERPRISE v4.1.53
      Conçu et développé par NunzioTech
```

## ❤️ Nuxiva est gratuit, et le restera

Nuxiva est un projet **totalement gratuit**, conçu, programmé et maintenu par **Nunzio Aprile (NunzioTech)** sur son temps libre :
aucun abonnement, aucune fonctionnalité payante dissimulée, aucune revente de données. Chaque ligne de code source vous appartient.

Si Nuxiva gère votre domicile, orchestre votre infrastructure, vous aide dans vos études ou propulse vos recherches, **un don est ce qui lui permet de continuer à grandir** : il finance le matériel de test (caméras, cartes ESP32, GPU, dispositifs edge), les crédits d'API pour les modèles cloud utilisés en développement et les milliers d'heures nécessaires à l'élaboration de nouvelles architectures autonomes.
Même le prix d'un café apporte une contribution concrète, et chaque don permet de rendre Nuxiva encore plus puissant pour chacun d'entre nous.

<p align="center">
  <a href="https://www.paypal.com/paypalme/NunzioAprile">
    <img src="https://img.shields.io/badge/Don-PayPal-00457C?style=for-the-badge&logo=paypal&logoColor=white" alt="Faire un don via PayPal">
  </a>
</p>

<p align="center"><b>👉 <a href="https://www.paypal.com/paypalme/NunzioAprile">paypal.me/NunzioAprile</a> — un grand merci pour votre soutien à l'ingénierie open source indépendante !</b></p>

---

## Architecture de Niveau Entreprise (Les 5 Piliers)

Nuxiva n'est pas un simple script ou une coquille logicielle autour d'une API, mais un **Système d'Exploitation Distribué et Autonome** reposant sur cinq piliers fondamentaux :

1. **Noyau Auto-Réparateur (eBPF & Landlock) :** Surveillance de bas niveau via des sondes C eBPF au sein du noyau Linux pour détecter les fuites de mémoire (MALLOC/FREE), anomalies de socket et appels suspects, déclenchant l'auto-réparation en direct par LLM.
2. **Exécution Isolée (Zero-Trust Wasm & MicroVMs) :** Aucun module tiers ou outil généré ne s'exécute directement sur la machine hôte. Le code est isolé au sein d'environnements WebAssembly (Wasmtime) avec règles WASI strictes (< 5ms de démarrage), conteneurs gVisor ou MicroVMs Firecracker dédiées.
3. **Voyage Temporel (Event Sourcing & Registre Immuable) :** Aucun état mutable direct. Chaque perception sensorielle, étape de pensée, delta biométrique et décision système est consigné dans un grand livre (Ledger) immuable signé par chaîne HMAC, autorisant le rejeu mathématique du système à la milliseconde près pour le débogage absolu.
4. **Calcul en Essaim (P2P Mesh Swarm) :** Nuxiva évolue horizontalement. La découverte automatique par balises UDP et mesh gRPC permet le délestage distribué des tenseurs visuels, signaux audio et inférences neuronales vers des nœuds GPU dédiés du réseau local.
5. **Génération Dynamique de SDK et Contrats :** Création automatique de bibliothèques clientes, contrats et routes d'API en TypeScript, Rust et Python via réflexion dynamique et schémas OpenAPI/Protobuf pour une interopérabilité sans faille.

---

## 1. En bref

| Aspect | Détails d'Implémentation |
| :--- | :--- |
| **Installation** | Une seule ligne sous Debian/Ubuntu : télécharge le dépôt dans `/opt/Nuxiva` et lance le superviseur autonome. |
| **Superviseur** | Service `nuxiva-supervisor` (Python 3.11+, FastAPI, asyncio). Exécute les 31 étapes d'installation du système d'exploitation, surveille la santé des services et gère les files d'attente. |
| **Affichage (Port 80)** | Kiosque interactif : visage holographique 3D (Orb), voix naturelle, écoute active, bureau à widgets dynamiques et sélecteur de mode de raisonnement. |
| **Panneau Admin (Port 8080)** | Interface d'administration complète avec authentification système PAM, télémétrie en direct, affectation des modèles, bascules de fonctionnalités et journaux système. |
| **Cerveau Cognitif** | 6 Moteurs de Raisonnement Modulaires (de Legacy 4.2 à Ultra 6.5), réseau de neurones impulsionnels LIF, Modulateur Limbique, Ollama local, grappes de serveurs et 22 fournisseurs cloud chiffrés. |
| **Écosystème Modulaire** | 72 modules auto-détectés dans `installer_wizard/features/`. Chaque module s'active automatiquement selon le matériel (`auto`) ou par forçage explicite (`1`/`0`). |
| **Mises à Jour Continues** | Synchronisation Git automatique toutes les 5 minutes depuis la branche `main` (uniquement si validée par la CI), avec vérification et retour arrière immédiat. Mise à niveau d'urgence via `nuxivactl update --force`. |
| **CEO Orchestrator & Équipe**| CEO Multi-Agent Orchestrator dynamique alimenté par `AgentScanner`. Aucun agent codé en dur : scanne `/features` et `/widgets` en direct et délègue selon l'indexation des tokens sémantiques. |
| **Compréhension et Triage** | Évaluation sémantique multi-fonctions, vérification déterministe des effets et triage clinique cognitif tri-agent (médical, psychologique, sécurité). |
| **Fiabilité et Rigueur** | Vérification post-exécution de l'effet physique réel avec nouvel essai automatique ; plus de 1 200 tests automatisés unitaires et d'intégration couvrant superviseur, cœur et crates Rust. |
| **Interopérabilité (MCP)** | Serveur (Port 8080) et client natif Model Context Protocol (MCP), export de schémas OpenAPI, appel de fonctions Anthropic/OpenAI et routes REST/WebSocket. |
| **Multilingue (i18n)** | Traduction intégrale à 100% en anglais, italien et français sur l'ensemble des écrans, fenêtres, widgets et messages du serveur. Téléchargement automatique des voix nécessaires. |

---

## 2. Évolution Architecturale et Historique des Versions

### Version 4.1.53 : L'Ère Neuro-Cognitive et Dynamique Universelle
- **Moteur Omni-Cortical Modulaire** : Découplage complet des moteurs de raisonnement (`BaseReasoningEngine`) dans `server/core/reasoning/engines/` avec découverte dynamique par `EngineScanner`.
- **Dynamique Neurale Neuro-Biologique** : Réseau impulsionnel Leaky Integrate-and-Fire (LIF) avec période réfractaire dynamique, plasticité synaptique STDP et modulation limbique à 7 dimensions.
- **Liaison Sensorielle-Limbique en Temps Réel** : Stress acoustique vocal, valence faciale et présence physique injectés dans le vecteur limbique cortical et diffusés en temps réel comme événements `biometrics.*` sur `nuxiva_bus`.
- **Default Mode Network (DMN)** : Cycle autonome de vagabondage cognitif déclenché après 10 minutes d'inactivité pour consolider les souvenirs et préparer des actions prédictives (foresight).
- **Consolidation Synaptique Nocturne REM** : Décroissance et stabilisation contrôlée des poids synaptiques STDP de la journée pour préserver les souvenirs importants de la courbe de l'oubli d'Ebbinghaus.
- **Scanner Dynamique Universel Accéléré en Rust** : Moteur `FastScanner` en Rust natif (`bus-core`) avec hachage FNV-1a, couplé à un `UniversalScanner` Python avec analyse syntaxique AST Zero-Trust et `DirectoryWatcher`.
- **Architecture de Widgets et Outils à Répertoires Dédiés** : Structure standardisée pour widgets dynamiques (`server/web/widgets/`) et outils d'agent (`server/features/agent_tools/`) avec auto-découverte et flux WebSocket.
- **CEO Multi-Agent Orchestrator** : Coordinateur général de conversation appuyé sur `AgentScanner` analysant les manifests et tokens sémantiques sans aucune liste fixe.
- **Triage Cognitif Clinique** : Agents spécialisés médical et psychologique avec verrouillage de sécurité déterministe pour les requêtes critiques.
- **File d'Attente Triée par Taille de Paquet** : Téléchargement en arrière-plan exécuté du plus petit composant en Go au plus grand avec tachymètre de vitesse en direct (Mo/s ou Ko/s).
- **Mise à Niveau Forcée par SSH** : Script de secours direct `force-upgrade.sh` et commande CLI `nuxivactl update --force`.
- **Robustesse Système** : Assistant d'éveil initial facultatif non bloquant et résolution du bogue de guillemets récursifs dans `/etc/nuxiva/nuxiva.env`.

### Version 4.0.0 : Swarm d'Entreprise et RBAC Spatio-Temporel
- **Contrôle d'Accès Spatio-Temporel (RBAC)** : Système d'autorisations combinant zones spatiales réelles (pièces/caméras) et plages horaires autorisées.
- **Essaim Multi-Agents Autonome** : Espaces de travail persistants et isolés (`data/agents/<agent_id>`), instructions dédiées, bases de connaissances et outils associés.
- **Chief Supervisor et War Room HUD** : Surveillance exécutive 24/7 prévenant les boucles infinies et retransmettant le graphe de pensée en direct.
- **Arsenal d'Outils Étendu** : Dessin technique CAD (DXF 2D/3D), suite Google Workspace (Gmail, Calendar, Drive, Sheets, Docs) et réseaux sociaux.
- **Raisonnement Ternaire** : Système 1 (routeur réactif rapide), Système 2 (boucle ReAct avec autocritique) et Système 3 (jury de consensus byzantin).
- **HUD de Proximité et Chatbot Mesh** : Réseau maillé pair-à-pair pour la collaboration instantanée entre agents et détection radar d'ambiance.
- **Administration Proxmox VE** : Pilotage complet de l'hypervisor pour machines virtuelles et conteneurs LXC.

### Version 3 : Réécriture Modulaire par Fonctionnalité et MCP
- **Architecture à Double Cerveau** : Système 1 non autorégressif ultrarapide (< 50ms) et Système 2 délibératif avec bloc de réflexion `<thinking>`.
- **Cockpit du Cerveau Réorganisé** : Tableau de bord, Affectations des composants et Gestion unifiée des modèles locaux, serveurs distants et cloud.
- **Grappe Neurale Distribuée** : Listes de priorités mixtes mêlant modèles Ollama locaux, serveurs réseau et 22 fournisseurs cloud.
- **Model Context Protocol (MCP)** : Implémentation native serveur et client MCP.
- **Vérification Réelle des Effets** : Contrôle effectif de l'état audio, domotique et des fenêtres après chaque commande.
- **Forge Autonome** : Synthèse sans programmation de nouveaux outils composés et widgets.

---

## 3. Prérequis Système

| Composant | Configuration Minimale | Configuration Recommandée |
| :--- | :--- | :--- |
| **Système d'Exploitation** | Debian 12 (Bookworm) ou Ubuntu 22.04+ LTS (x86_64 / arm64) | Debian 12 Minimal (x86_64) |
| **Processeur (CPU)** | 4 cœurs (x86_64 avec AVX ou ARM64 v8.2+) | 8+ cœurs avec AVX2 / AVX-512 |
| **Mémoire Vive (RAM)** | 8 Go de mémoire système | 16–32 Go DDR4/DDR5 |
| **Carte Graphique (GPU)** | Aucune (inférence supportée sur CPU seul) | NVIDIA RTX (8 Go+ VRAM) avec CUDA 12+ ou Apple Silicon |
| **Stockage** | 30 Go d'espace libre sur disque | 100+ Go SSD NVMe (modèles, voix, enregistrements) |
| **Connexion Réseau** | Accès Internet haut débit pour l'installation | Connexion filaire Gigabit Ethernet |
| **Périphériques** | Fonctionnement autonome (headless) supporté | Microphone, haut-parleurs stéréo, webcam USB/IP, écran |

> [!NOTE]
> - Le processus d'installation utilise `apt-get` : **seules les distributions Debian, Ubuntu et leurs dérivées directes sont supportées**.
> - En l'absence de GPU dédié, Nuxiva sélectionne automatiquement des modèles quantifiés légers et optimisés (ex. Q4_K_M de 1,5B à 3B paramètres).
> - Les configurations modestes peuvent délester le calcul neuronal vers un autre serveur distant (`NUXIVA_OLLAMA_URL`) ou utiliser des modèles cloud.
> - Les fonctions exigeant du matériel spécifique (caméra, micro, accélération GPU) se désactivent d'elles-mêmes en mode `auto` si le périphérique est absent.

---

## 4. Installation

### Commande Unique (Recommandée pour Debian/Ubuntu)

Exécutez cette commande dans un terminal avec les privilèges sudo :

```bash
curl -fsSL https://raw.githubusercontent.com/aprilenunzio88/Nuxiva/main/install.sh | bash
```

Le script effectue les diagnostics préalables, télécharge le dépôt dans `/opt/Nuxiva`, configure les droits d'accès, installe Python et les outils de base, puis active le service `nuxiva-supervisor`. Le superviseur prend immédiatement le relais et pilote le reste de la configuration de façon autonome.

### Installation Manuelle depuis un Clone du Dépôt

```bash
# 1. Cloner le dépôt officiel
sudo git clone https://github.com/aprilenunzio88/Nuxiva.git /opt/Nuxiva
cd /opt/Nuxiva

# 2. Lancer le script d'installation
sudo bash install.sh
```

### Déploiement sous Windows

Sous Windows, Nuxiva est officiellement supporté via **WSL2 (Windows Subsystem for Linux)** avec Ubuntu 22.04 ou Debian 12 :

```powershell
# Dans PowerShell ouvert en Administrateur :
wsl --install -d Ubuntu-22.04
wsl
```
Dans l'environnement Linux WSL2, exécutez simplement la commande d'installation :
```bash
curl -fsSL https://raw.githubusercontent.com/aprilenunzio88/Nuxiva/main/install.sh | bash
```
Pour une expérimentation native sous Windows, un script PowerShell d'administration est fourni :
```powershell
.\install.ps1
```

---

## 5. Premier Démarrage, Accès et Installations en Arrière-Plan

### Ports et Portails Web d'Accès

Une fois le superviseur en fonction, Nuxiva ouvre deux portails d'accès distincts :

1. **Affichage Interactif / Kiosque (Port 80) :** `http://<ip-serveur>/`
   - Visage 3D interactif (Orb) réagissant à la voix, aux sons et aux mouvements.
   - Bureau de widgets dynamiques affichés en temps réel.
   - Sélecteur de Moteurs Cognitifs : basculez le mode de raisonnement à la volée.
   - Session kiosque plein écran lancée automatiquement sur les écrans physiques reliés au serveur.
2. **Poste de Contrôle Administrateur (Port 8080) :** `http://<ip-serveur>:8080/`
   - Gestion complète du système protégée par authentification système Linux PAM (comptes root ou sudoers).
   - Télémétrie en direct, gestion des modèles, listes de priorités, configuration des modules et consultation des journaux.

### Configuration Initiale d'Éveil Modulaire et Optionnelle

L'assistant de premier démarrage (`/setup` sur le Port 80) est **totalement facultatif et non bloquant** :
- Vous pouvez suivre les étapes pour personnaliser le nom de l'assistant, connecter le réseau, étalonner le micro et choisir une voix.
- Vous pouvez librement ignorer cette étape pour basculer directement vers le bureau interactif standard.
- La configuration peut être relancée ou modifiée ultérieurement depuis le panneau d'administration sans interruption de service.

### File d'Attente en Arrière-Plan avec Vitesse et Ordre par Taille

Les éléments les plus volumineux (poids de modèles d'IA, réseaux neuronaux visuels, packs de voix, conteneurs) sont déployés de manière asynchrone pour que l'assistant soit opérationnel sans attendre :
- **Mesure de Débit en Direct** : L'interface de la file d'attente (`bgqueue.js/css`) affiche la vitesse réelle de téléchargement (en Mo/s ou Ko/s), la barre d'avancement et le pourcentage.
- **Ordre de Taille Croissant (Go)** : La file s'exécute dans l'ordre strict du paquet le plus léger au plus lourd en gigaoctets. Les utilitaires légers sont prêts en quelques secondes.
- **Suivi en Ligne de Commande** : Vérifiez l'avancement de la file à tout moment :
  ```bash
  nuxivactl background
  ```

---

## 6. Architecture Générale du Système

```text
+---------------------------------------------------------------------------------------+
|                                  RUNTIME DE NUXIVA                                    |
+---------------------------------------------------------------------------------------+
|  INTERFACES CLIENT                                                                    |
|  - Écran Kiosque (Port 80) : Sphère 3D, Audio STT/TTS, Bureau de Widgets, UI Moteurs  |
|  - Cockpit Admin (Port 8080) : Authentification PAM, Télémétrie, Modèles, Journaux    |
|  - Client Web React (client_web) : Control Deck, Visualiseur 3D, DynamicWidgetDeck    |
|  - Satellites P2P et APK Android : Nœuds edge audio/vidéo, Radar de proximité         |
+---------------------------------------------------------------------------------------+
|  SUPERVISEUR ET MOTEUR D'ARRIÈRE-PLAN (installer_wizard/backend/ - Python / FastAPI)  |
|  - Démon Superviseur (nuxiva-supervisor.service)                                      |
|  - Orchestrateur des 31 Étapes OS et Registre d'État (state.json, ledger.log)        |
|  - Watchdog des Boucles et Default Mode Network (DMN - cycle de réflexion / 10 min)  |
|  - CEO Multi-Agent Orchestrator et AgentScanner dynamique (features/team/ceo.py)     |
|  - 72 Fonctionnalités Système et Contrôleur de Widgets Dynamiques (/widgets, /ws)     |
+---------------------------------------------------------------------------------------+
|  CŒUR COGNITIF ET MOTEURS DE RAISONNEMENT (server/core/ & server/features/)           |
|  - Omni-Cortical Engine 6.5 et Registre Dynamique des BaseReasoningEngine             |
|    [ Legacy 4.2 | Veloce 5.0 | Empatico 5.0 | Pro 6.0 | Ultra 6.5 | Auto 6.5 ]      |
|  - Cœur Spiking Neural Network Leaky Integrate-and-Fire (LIF) et Plasticité STDP     |
|  - Modulateur Limbique à 7 Axes (Valence, Arousal, Dominance, DA, NE, 5-HT, Cortisol) |
|  - Liaison Sensorielle Directe (Stress vocal, Pression de scène, Présence physique)   |
|  - Global Neuronal Workspace (GNW) : Parallélisme spéculatif et inhibition GABA       |
|  - Triage Clinique Cognitif Tri-Agent (Médical, Psychologique, Verrou de Sécurité)   |
|  - Outils d'Agent Dynamiques (CAD, Modélisation 3D, Google, Images, Cartes, Musique) |
|  - Consolidation Synaptique Nocturne REM contre la Courbe de l'Oubli d'Ebbinghaus     |
+---------------------------------------------------------------------------------------+
|  BUS D'ÉVÉNEMENTS ET COUCHE NATIVE RUST HAUTE PERFORMANCE (native/crates/ - Rust/PyO3)|
|  - bus-core : Acheminement zéro-copie, RingBufferLockFree d'impulsions, FastScanner  |
|  - egress : Proxy réseau et bac à sable Zero-Trust avec confinement Linux Landlock    |
|  - netguard : Inspection approfondie des paquets (DPI) et pare-feu réseau             |
|  - nuxiva-native : Liaisons PyO3 exposant les structures Rust au runtime Python       |
+---------------------------------------------------------------------------------------+
|  ESPACES DE TRAVAIL ISOLÉS ET RUNTIME DU SYSTÈME (Noyau Linux et Bacs à Sable)        |
|  - Environnement WebAssembly Zero-Trust (Wasmtime) et MicroVMs (Firecracker / gVisor) |
|  - Espaces de travail persistants (data/agents/<agent_id>/) et Registre d'Événements  |
|  - Sondes eBPF Linux, ZRAM/Swap, Docker CE, Runtime Ollama, PipeWire/ALSA             |
+---------------------------------------------------------------------------------------+
```

### Le Cycle Cognitif d'une Requête

1. **Perception Sensorielle** : Le flux vocal est capturé par `features/ear/` (Whisper STT) ou l'image par `features/vision/` (YOLO/VLM).
2. **Modulation Sensorielle-Limbique** : Le stress vocal et l'expression faciale mettent à jour le `LimbicModulator` à 7 axes et émettent des données sur `nuxiva_bus`.
3. **Orchestration CEO et Compréhension** : Le CEO Orchestrator consulte `AgentScanner` pour comparer la requête aux capacités et outils déclarés des agents.
4. **Sélection du Moteur Cognitif** : L'Omni-Cortical Engine sélectionne la stratégie de réflexion (ex. `nuxiva-6.5-auto` arbitre selon la complexité $\psi$, l'état émotionnel et la VRAM).
5. **Exécution Parallèle Spéculative (GNW)** : Jusqu'à 16 branches de réflexion avancent simultanément. Lorsqu'une branche atteint le seuil d'allumage, elle émet une **inhibition latérale GABAergique** qui annule instantanément les branches concurrentes plus lentes.
6. **Verrouillage de Sécurité et Consensus Byzantin** : Les actions physiques critiques ou médicales passent par des verrous déterministes et un jury de modèles indépendants avec droit de veto.
7. **Exécution en Bac à Sable Isolé** : Les outils d'agent ou actions de commande s'exécutent dans des environnements confinés.
8. **Vérification Réelle de l'Effet** : Le système contrôle l'effet concret (ex. lecture de musique lancée, widget affiché) avant de confirmer l'action.
9. **Apprentissage Synaptique STDP** : Les connexions synaptiques entre neurones activés adaptent leurs forces selon la règle Hebbienne STDP pour mémoriser l'expérience.

---

## 7. Structure du Dépôt

```text
/opt/Nuxiva/
├── client_apk/                  # Application native pour smartphones Android (Kotlin)
├── client_satellite/            # Démon satellite léger pour nœuds edge ESP32 / Raspberry Pi
├── client_web/                  # Application web moderne React 18 + Vite + Tailwind + Three.js
│   ├── src/features/
│   │   ├── cognitive_engine/    # Sélecteur d'interface et hooks des moteurs cognitifs
│   │   ├── control_deck/        # Cockpit de contrôle et flux d'analyse neurale en temps réel
│   │   ├── core_visualizer_3d/  # Visualiseur 3D des impulsions neurales et affichage tête haute
│   │   ├── dynamic_widgets/     # DynamicWidgetDeck et rendu en direct des widgets dynamiques
│   │   └── studio_3d/           # Studio de modélisation et conception 3D/CAD paramétrique
│   └── src/shared/i18n/         # Catalogues complets de localisation (EN, IT, FR)
├── data/                        # Données persistantes, espaces de travail des agents, coffres
│   └── agents/<agent_id>/       # Espaces de travail isolés et persistants pour chaque agent
├── docker/                      # Définitions de conteneurs de production
├── installer_wizard/            # Démon du superviseur et interface d'administration
│   ├── backend/                 # Serveur FastAPI du superviseur, boucles, nuxiva_bus, file d'attente
│   ├── features/                # 72 fonctionnalités système modulaires auto-détectées
│   │   ├── brain/               # Profils du cerveau, composants LIF, affectations, rétention VRAM
│   │   ├── chat/                # Pipeline de dialogue, brain_chain (GNW), points d'accès API
│   │   ├── team/                # CEO Orchestrator, AgentScanner dynamique, tableau de bord partagé
│   │   ├── ear/                 # Transcription vocale, stress acoustique, biométrie vocale
│   │   ├── vision/              # Détection VLM, suivi d'objets YOLO, consolidation nocturne
│   │   └── ...                  # 67 fonctionnalités spécialisées complémentaires
│   └── web/                     # Interfaces web (display, admin, nexus, monitor, setup)
├── native/                      # Modules haute performance écrits en langage Rust
│   └── crates/
│       ├── bus-core/            # FastScanner (FNV-1a), Cœur Neurnal Spiking, RingBufferLockFree
│       ├── egress/              # Proxy réseau et bac à sable Zero-Trust avec Linux Landlock
│       ├── langid/              # Identification instantanée de la langue parlée
│       ├── netguard/            # Pare-feu d'inspection approfondie des paquets (DPI)
│       └── nuxiva-native/       # Liaisons PyO3 exposant les crates Rust au code Python
├── sandbox_broker/              # Gestionnaire de bacs à sable conteneurisés et MicroVMs
├── scripts/os/                  # Les 31 scripts d'installation du système et de maintenance
│   ├── steps/                   # Scripts numérotés de 10-preflight.sh à 95-warmup.sh
│   ├── force-upgrade.sh         # Script de mise à niveau forcée et restauration directe depuis GitHub
│   └── nuxivactl                # Binaire CLI principal d'administration système
├── server/                      # Cœur Cognitif de Nuxiva (Python 3.11+)
│   ├── cmd/                     # Routeurs API, point d'entrée, FeatureRouteScanner
│   ├── core/
│   │   ├── kernel/              # Consensus byzantin, état limbique, voies de communication de l'essaim
│   │   ├── orchestrator/        # Routeur Système 1, planificateur en graphe DAG, synthèse d'outils
│   │   ├── reasoning/           # Moteur Omni-Cortical et moteurs de raisonnement modulaires
│   │   │   └── engines/         # auto_6_5, ultra_6_5, pro_6_0, empatico_5_0, veloce_5_0, legacy_4_2
│   │   └── scanner/             # UniversalScanner, ZeroTrustValidator, DirectoryWatcher
│   ├── features/
│   │   ├── agent_tools/         # Outils d'agent : cad, 3d, google, image, cartes, musique, scraping
│   │   ├── cognitive_triage_agents/ # Triage clinique cognitif (médical, psychologique, sécurité)
│   │   └── multimodal_surveillance/ # Fusion affective, hub pour objets connectés, audio enhancer
│   └── web/widgets/             # Widgets dynamiques modulaires (manifest.json, BaseWidget, contrôleur)
├── install.sh                   # Script d'amorçage automatique pour Debian/Ubuntu
├── install.ps1                  # Script d'amorçage PowerShell pour environnement Windows
├── docker-compose.yml           # Déploiement multi-conteneurs du système
└── VERSION                      # Numéro de version du système (4.1.53)
```

---

## 8. Le Superviseur et le Moteur d'Arrière-Plan

Le service système `nuxiva-supervisor.service` fonctionne en continu pour assurer l'auto-réparation et la pérennité du système :

### Watchdog des Services d'Arrière-Plan (`installer_wizard/backend/loops.py`)
- **Détection des Pannes et Relance Automatique** : Surveille régulièrement l'activité des boucles internes. Si un processus se bloque ou s'arrête de manière inattendue, le superviseur le redémarre avec un délai exponentiel maîtrisé (`NUXIVA_LOOPS_BACKOFF_MAX`).
- **Surveillance des Battements (Heartbeat)** : Chaque tâche transmet un battement de vie régulier. En cas d'absence de réponse dépassant le seuil admissible ($5 \times \text{période}$), le superviseur met fin au thread défaillant et le réinstancie proprement.

### Default Mode Network (DMN) : Cycle de Réflexion Autonome
- **Activation sur Période d'Inactivité** : Lorsque l'utilisateur cesse d'interagir pendant au moins 10 minutes consécutives (`idle_threshold_s = 600.0`), le DMN démarre automatiquement.
- **Consolidation des Connaissances** : Le DMN interroge la mémoire à long terme (`LongTermMemory`) et croise les faits observés avec les habitudes apprises dans `features/habits/foresight.py`.
- **Simulation Proactive** : Lance un cycle de pensée spéculatif via `cortical_chain.execute_parallel_thought()`, pré-calculant des routines utiles et préchauffant les caches de données.
- **Interruption Immédiate** : La moindre commande vocale ou interaction par chat réinitialise instantanément le compteur du DMN pour ne jamais ralentir l'utilisation directe.

---

## 9. Étapes d'Installation du Système d'Exploitation (Les 31 Scripts)

Nuxiva déploie et paramètre l'environnement système via 31 scripts numérotés et indépendants situés dans `scripts/os/steps/` :

| Script d'Étape | Désignation | Rôle et Actions Réalisées |
| :--- | :--- | :--- |
| `10-preflight.sh` | Diagnostics Initiaux | Vérifie la version du système, l'architecture (x86_64/arm64), les cœurs CPU, la RAM et le disque disponible. |
| `15-memory.sh` | Mémoire et ZRAM | Configure l'espace de swap compressé en ZRAM et optimise les règles de gestion de la mémoire du noyau. |
| `20-system.sh` | Paquets Essentiels | Installe les utilitaires Linux, les compilateurs de base, curl, git, jq et les bibliothèques Python. |
| `25-kiosk.sh` | Affichage Kiosque | Prépare l'environnement graphique léger (X11/Cage/Chromium) pour le plein écran sur le Port 80. |
| `30-docker.sh` | Moteur de Conteneurs | Installe et configure le moteur Docker CE et le service containerd. |
| `32-sandbox.sh` | Bacs à Sable Isolés | Met en place les arborescences de fichiers nécessaires à l'exécution confinée des outils d'agents. |
| `33-display-driver.sh`| Pilotes Graphiques | Configure les pilotes d'accélération d'affichage vidéo (Mesa, DRM/KMS, Xorg). |
| `34-gvisor.sh` | Bac à Sable gVisor | Déploie le runtime de conteneurs `runsc` de Google avec noyau en espace utilisateur pour accès réseau confiné. |
| `35-gpu.sh` | Accélération GPU | Détecte et configure le support NVIDIA CUDA, AMD ROCm ou Intel oneAPI dans les conteneurs. |
| `36-firecracker.sh` | Hyperviseur MicroVM | Installe l'hyperviseur KVM Firecracker pour lancer des MicroVMs ultra-légères en quelques millisecondes. |
| `38-native.sh` | Modules Natifs Rust | Compile via Cargo les crates Rust haute performance (`bus-core`, `egress`, `langid`, `netguard`, `nuxiva-native`). |
| `40-security.sh` | Sécurisation Système | Règle les profils AppArmor, les politiques PAM, le pare-feu (UFW/nftables) et les droits sur les fichiers. |
| `42-netguard.sh` | Inspection DPI | Installe le moteur d'inspection approfondie des paquets pour protéger le réseau local contre les anomalies. |
| `43-vpn.sh` | Réseau Mesh VPN | Configure un réseau privé virtuel sécurisé de type maillé basé sur WireGuard et Tailscale. |
| `50-ollama.sh` | Moteur LLM Ollama | Prépare le service Ollama avec des variables d'environnement assainies et un démarrage différé si non configuré. |
| `55-voice.sh` | Synthèse Vocale | Installe les moteurs de synthèse vocale neurale Piper TTS et Kokoro pour la restitution audio. |
| `56-bluetooth.sh` | Bluetooth et Audio | Règle la pile logicielle BlueZ et PipeWire pour la connexion de micros et enceintes sans fil. |
| `57-vision.sh` | Vision Artificielle | Déploie OpenCV, OpenVINO, les modèles de détection d'objets YOLO et les pipelines visuels VLM. |
| `58-ear.sh` | Reconnaissance Audio | Installe la transcription vocale Whisper STT, la mesure du stress acoustique et l'empreinte de la voix. |
| `59-music.sh` | Bibliothèque Audio | Configure l'indexation musicale, la reconnaissance acoustique, ainsi que les serveurs DLNA et Chromecast. |
| `60-models.sh` | Téléchargement IA | Télécharge les premiers modèles d'IA par ordre de taille croissant en Go avec affichage de la vitesse. |
| `61-brain.sh` | Cerveau Cognitif | Règle les routes d'affectation des modèles et initialise l'orchestrateur Omni-Cortical. |
| `62-convert3d.sh` | Outils CAD et 3D | Installe les bibliothèques de manipulation de maillages et de conversion géométrique DXF 2D/3D. |
| `63-shares.sh` | Partages de Fichiers | Configure les partages réseau Samba (SMB/CIFS) compatibles avec Windows 11, Mac et Linux. |
| `64-office.sh` | Traitement Documents | Installe LibreOffice en mode sans interface pour l'extraction de texte et conversion automatique de PDF. |
| `66-voicestudio.sh` | Voice Studio | Déploie le conteneur optionnel XTTS pour le clonage de voix avec contrôle de l'espace disque. |
| `67-soup.sh` | Model Souping | Configure les utilitaires d'interpolation des poids neuronaux pour l'apprentissage autonome hors ligne. |
| `70-core.sh` | Cœur Nuxiva | Installe les dépendances Python du serveur, les schémas de base de données Alembic et lance les démons. |
| `80-services.sh` | Démarrage Services | Active et démarre l'ensemble des services système systemd (`nuxiva-core`, `nuxiva-supervisor`, etc.). |
| `90-maintenance.sh` | Tâches de Maintenance| Met en place les scripts de nettoyage automatique des journaux et de gestion de l'espace disque. |
| `95-warmup.sh` | Préchauffage Modèles | Exécute des inférences tests pour précharger les réseaux de neurones en RAM/VRAM avant la première requête. |

---

## 10. Le Cerveau Cognitif : Architecture, Moteurs de Raisonnement et Neuro-Biologie

### Les 6 Moteurs de Raisonnement Modulaires (`server/core/reasoning/engines/`)

Le noyau cognitif de Nuxiva repose sur l'Open/Closed Principle. Chaque moteur hérite de `BaseReasoningEngine` et est découvert dynamiquement par `EngineScanner` :

| Version Moteur | Nom de Code | Architecture et Stratégie Cognitive | SLA Latence | Budget VRAM | Rôle Attribué |
| :--- | :--- | :--- | :---: | :---: | :---: |
| `nuxiva-4.2-legacy` | **Legacy Chain-Sync** | Pipeline séquentiel à jetons avec secours en série | 2500 ms | 2048 Mo | Secours |
| `nuxiva-5.0-veloce` | **Veloce Synapse-Flash** | Ternary 1.58-bit avec Liquid LNN et bus impulsionnel | 25 ms | 512 Mo | Chat Rapide |
| `nuxiva-5.0-empatico`| **Empatico Synapse-Limbic** | Global Workspace 8 voies parallèles et biométrie à 10Hz | 120 ms | 4096 Mo | Dialogue/Voix |
| `nuxiva-6.0-pro` | **Pro Omni-Latent** | Espace Latent Continu JEPA/Coconut avec plasticité VRAM | 15 ms | 8192 Mo | Code/Logique |
| `nuxiva-6.5-ultra` | **Ultra DeepThink-MCTS** | MCTS latent 64 branches avec modèle de récompense PRM | 650 ms | 16384 Mo | Recherche/CAD |
| `nuxiva-6.5-auto` | **Auto Thalamic-Adaptive** | Méta-orchestrateur thalamique basé sur l'énergie libre | 45 ms | Dynamique | **Par Défaut** |

#### Logique d'Arbitrage Thalamique Dynamique (`nuxiva-6.5-auto`)
En mode automatique, le méta-orchestrateur calcule le facteur de complexité cognitive $\psi \in [0.0, 1.0]$ à partir de l'entropie des jetons et de la surprise informationnelle :
- $\psi < 0.25$ : aiguille directement vers `nuxiva-5.0-veloce` (réponse réactive immédiate).
- $\psi < 0.50$ ou niveau d'éveil émotionnel élevé : aiguille vers `nuxiva-5.0-empatico` (dialogue chaleureux adapté au ton de la voix).
- $0.50 \le \psi < 0.75$ : aiguille vers `nuxiva-6.0-pro` (raisonnement analytique et exécution d'outils).
- $\psi \ge 0.75$ : aiguille vers `nuxiva-6.5-ultra` (recherche approfondie MCTS avec autocritique du Jumeau Numérique).

### Dynamique Neurale Impulsionnelle Leaky Integrate-and-Fire (LIF)

Le moteur neuro-biologique (`installer_wizard/features/brain/components.py` et `native/crates/bus-core/src/spike.rs`) reproduit la transmission synaptique selon le modèle LIF :

$$\tau_m \frac{dV(t)}{dt} = -(V(t) - V_{\text{rest}}) + R \cdot I(t)$$

- **Intégration et Fuite** : À chaque impulsion entrante, le potentiel de membrane s'élève en proportion du poids synaptique $w_{ij}$ et de la résistance $R$, puis décroît vers son niveau de repos selon la constante de temps $\tau_m$.
- **Période Réfractaire Modulée par la Noradrénaline** : Après décharge, le neurone se réinitialise à $V_{\text{reset}}$ et entre en période réfractaire absolue :
  $$t_{\text{réfractaire}} = t_{\text{actuel}} + \max(0.005, 0.04 \cdot (1.0 - 0.6 \cdot \text{Noradrénaline}))$$
  Une poussée de noradrénaline (situation d'urgence ou d'alerte) raccourcit la période réfractaire, accélérant le débit cognitif.
- **Seuil de Décharge Ajusté par l'État Limbique** :
  $$\theta = \max\left(0.12, \theta_{\text{base}} \cdot (1.0 - 0.45 \cdot \text{Noradrénaline}) + 0.15 \cdot \text{Cortisol}\right)$$
- **Plasticité Synaptique Hebbienne STDP** : Les connexions s'ajustent en fonction de l'intervalle de temps entre impulsion pré- et post-synaptique ($\Delta t = t_{\text{post}} - t_{\text{pre}}$) :
  $$\Delta w = \begin{cases} A^+ e^{-\Delta t / \tau_{\text{stdp}}} \cdot R_{\text{dopamine}} & \text{si } \Delta t > 0 \quad (\text{Potentialisation à Long Terme / LTP}) \\ -A^- e^{\Delta t / \tau_{\text{stdp}}} & \text{si } \Delta t < 0 \quad (\text{Dépression à Long Terme / LTD}) \end{cases}$$

### Modulateur Limbique à 7 Axes et Liaison Sensorielle

L'état émotionnel interne de Nuxiva évolue en continu le long de sept dimensions biochimiques :

| Axe Limbique | Intervalle | Modulé par | Fonction dans le Système |
| :--- | :---: | :--- | :--- |
| **Valence** | $[-1.0, +1.0]$ | Expression du visage (caméra), analyse du ton du texte | Tonalité globale du ressenti (positif/négatif) |
| **Arousal** | $[0.0, 1.0]$ | Stress acoustique vocal (micro), rythme cardiaque | Niveau d'activation et de vigilance cognitive |
| **Dominance** | $[0.0, 1.0]$ | Clarté et autorité de la commande de l'utilisateur | Assurance et fermeté dans la réponse |
| **Dopamine** | $[0.05, 1.0]$ | Réussite des actions, curiosité, validation positive | Budget d'exploration créative et renforcement STDP |
| **Noradrénaline**| $[0.05, 1.0]$ | Alarmes, pression de l'environnement, requêtes urgentes| Accélération des fréquences d'impulsion neuronales |
| **Sérotonine** | $[0.05, 1.0]$ | Régularité des échanges, respect des habitudes | Stabilité globale et sérénité de l'assistant |
| **Cortisol** | $[0.05, 1.0]$ | Pannes inattendues, résultats non vérifiés, alertes | Réduction des spéculations et sécurité stricte |

#### Liaison Sensorielle Directe
- **Ear / Voiceprint** : Mesure le micro-tremblement vocal et la distribution spectrale pour évaluer le stress acoustique de l'utilisateur et ajuster l'`arousal` et la `noradrénaline`.
- **Scene / Fusion** : Détecte les mimiques faciales et l'activité de la pièce pour évaluer la `valence_faciale` et la `pression_ambiante`.
- **People / Presence** : Intègre les données biométriques et publie les mises à jour sur le bus sous forme d'événements `biometrics.vocal_stress`, `biometrics.facial_valence` et `biometrics.limbic_vector`.

### Global Neuronal Workspace (GNW) et Inhibition Latérale GABAergique

Dans `installer_wizard/features/chat/brain_chain.py`, les demandes complexes mobilisent le Global Neuronal Workspace :
1. **Parallélisme Spéculatif** : Déploiement simultané de jusqu'à 16 hypothèses de réflexion sur des modèles distincts.
2. **Allumage de la Branche** : Chaque branche progresse par étapes MCTS, vérifiée par le simulateur du Jumeau Numérique (`predict_user_impact`).
3. **Inhibition Latérale GABAergique** : Dès qu'une hypothèse franchit le seuil d'allumage ($\ge 0.85$), elle déclenche une inhibition latérale immédiate qui annule (`task.cancel()`) toutes les branches concurrentes plus lentes en quelques microsecondes.
4. **Restitution du Résultat** : La pensée gagnante est transmise avec son empreinte limbique et ses métriques de latence réelles.

### Consolidation Synaptique Nocturne (Sommeil REM)

Pendant la maintenance nocturne (`features/vision/nightly.py` et `features/soup/trainer.py`) :
- Les synapses stimulées pendant la journée font l'objet d'un rééquilibrage homéostatique :
  $$w_{t+1} = w_t \cdot \gamma + (1 - \gamma) \cdot w_{\text{base}}$$
- Les connexions associées à des faits marquants (`compute_emotional_salience`) sont définitivement gravées dans la mémoire à long terme, évitant l'érosion naturelle modélisée par la courbe d'Ebbinghaus.

---

## 11. Catalogue des Fonctionnalités (72 Modules Auto-Détectés)

Nuxiva intègre 72 fonctionnalités modulaires regroupées dans `installer_wizard/features/`. Chacune dispose de son fichier `feature.json` et s'active automatiquement en mode `auto` dès que les prérequis matériels sont réunis :

### Assistant et Dialogue Cognitif
- `chat` : Dialogue multi-moteurs, exécution spéculative GNW et streaming des réponses.
- `brain` : Sélection du mode de réflexion, neurones LIF, listes de priorités et rétention en VRAM.
- `mind` : Mémoire épisodique, rappel sémantique, journal de bord quotidien et score de rétention d'Ebbinghaus.
- `understanding` : Notation sémantique multi-fonctions et arbitrage contextuel des intentions.
- `team` : CEO Multi-Agent Orchestrator dynamique et `AgentScanner` sans inventaire figé.
- `capabilities` : Déclaration dynamique des capacités et outils transmise en tête de contexte à chaque modèle.
- `habits` : Observation automatique des habitudes de vie avec système de pénalité en cas d'annulation.
- `autonomy` : Tâches planifiées vocalement, pilote automatique toutes les 30 minutes et bilans du soir.
- `laws` : Quatre lois inviolables et règles de conduite injectées dans chaque processus de pensée.
- `soup` : Ajustement fin des modèles (fine-tuning), fusion de poids et apprentissage autonome.
- `study` : Étude autonome durant les temps de veille : assimilation de documents et auto-évaluation.
- `twin` : Jumeau numérique du domicile : valide tout plan domotique ou vocal avant exécution réelle.
- `forge` : Création instantanée de nouveaux outils et widgets personnalisés sans écrire de code.

### Perception et Biométrie
- `ear` : Prise de son microphonique, Whisper STT, reconnaissance de l'empreinte vocale et stress acoustique.
- `voices` : Plus de 600 voix neurales dans plus de 60 langues (Kokoro, Piper, Edge TTS).
- `voicestudio` : Conteneur optionnel XTTS dédié au clonage de voix haute fidélité.
- `ducking` : Atténuation intelligente et fluide du volume de la musique lorsque Nuxiva s'exprime.
- `vision` : Analyse d'images, détection d'objets YOLO, modèles de vision VLM et reconnaissance OCR.
- `cameras` : Affichage en direct de flux webcam/IP et interrogation visuelle interactive à la voix.
- `nvr` : Enregistrement de vidéosurveillance sur disque, événements MQTT et recherche visuelle en langage naturel.
- `scene` : Représentation spatiale 3D : localise objets et meubles dans le champ visuel des caméras.
- `biometrics` : Fusion biométrique en direct (stress vocal, émotions du visage, rythme cardiaque).
- `hands` : Reconnaissance des gestes de la main face à la webcam (pincement, glissement, zoom).
- `people` : Reconnaissance faciale avec détection de vivacité et suivi continu de présence.
- `presence` : Détection multi-capteurs estimant la présence humaine pièce par pièce.

### Maison Connectée et Robotique Spatiale
- `home_assistant` : Passerelle bidirectionnelle avec Home Assistant via API REST et WebSocket.
- `automations` : Création visuelle ou vocale d'automatisations avec embranchements et conditions imbriquées.
- `devices` : Détection automatique des appareils du réseau local (mDNS, UPnP, SSDP, Zigbee, Z-Wave).
- `bluetooth` : Gestion des périphériques Bluetooth Low Energy et appairage d'enceintes ou écouteurs.
- `tv` : Détection et contrôle des téléviseurs connectés (Android TV, LG webOS, Samsung Tizen).
- `printers` : Prise en charge des imprimantes de réseau IPP Everywhere et envoi automatique d'impressions 3D.
- `places` : Définition de zones géographiques, barrières virtuelles (geofencing) et trajets.
- `proxmox` : Gestion directe d'environnements Proxmox VE pour surveiller machines virtuelles et conteneurs LXC.
- `rpa` : Automatisation visuelle du poste de travail : repérage d'éléments à l'écran, clics et saisie au clavier.

### Médias et Connaissances
- `music` : Bibliothèque musicale locale, empreinte sonore, récupération de pochettes, streaming DLNA et Chromecast.
- `spotify` : Pilotage à distance des flux Spotify Connect.
- `sounds` : Bibliothèque de bruitages sonores et retours auditifs du système.
- `documents` : Analyse sémantique de fichiers (PDF, DOCX, TXT) et génération de synthèses documentaires.
- `models3d` : Conception 3D paramétrique, génération de fichiers STL/OBJ et visionneuse WebGL intégrée.
- `shares` : Partages réseau Samba (SMB/CIFS) et NFS pour postes Windows, macOS et Linux.
- `sports` : Suivi en temps réel des résultats sportifs, classements et calendriers de compétitions.
- `whiteboard` : Tableau blanc interactif plein écran avec résolution assistée d'équations et tracé de fonctions.

### Système, Sécurité et Infrastructure
- `authz` : Contrôle d'accès spatio-temporel (RBAC) associant localisation dans les pièces et horaires d'accès.
- `vault` : Coffre chiffré AES-256 pour les clés d'API cloud, jetons de service et mots de passe.
- `secure` : Surveillance continue de la sécurité, intégrité des droits et détection d'intrusions.
- `firewall` : Gestion dynamique du pare-feu et filtrage des flux de communication.
- `netguard` : Blocage et surveillance du trafic réseau suspect au niveau de la passerelle locale.
- `vpn` : Réseau virtuel maillé chiffré de bout en bout (WireGuard, Tailscale).
- `network` : Télémétrie des interfaces réseau, configuration DNS et analyse des débits.
- `kiosk` : Gestion de l'affichage plein écran sur session X11/Cage et extinction automatique du moniteur.
- `desktop` : Organisation visuelle des fenêtres et disposition des widgets sur le bureau.
- `appearance` : Thèmes esthétiques de l'interface (cyberpunk, glassmorphism, sombre/clair).
- `avatars` : Personnalisation visuelle du visage holographique 3D de l'assistant.
- `nexus` : Interface futuriste cyberpunk avec sphère animée, graphismes vectoriels et HUD.
- `nodes` : Découverte des nœuds du maillage Nuxiva et appairage de satellites par jeton unique.
- `mcpclient` : Passerelle de connexion vers des serveurs externes Model Context Protocol (MCP).
- `google` : Intégration de la suite Google Workspace (Gmail, Calendar, Drive, Contacts).
- `maps` : Calcul d'itinéraires routiers ou piétons et recherche de points d'intérêt cartographiques.
- `telegram` : Bot Telegram bidirectionnel avec transcription audio et envoi d'images.
- `redalert` : Alerte de sécurité maximale : déclenchement de sirènes, messages d'urgence et verrouillage.
- `governor` : Régulation des ressources : surveillance thermique, charge CPU et limitation des tâches lourdes.
- `scheduler` : Planificateur temporel de haute précision orchestrant les événements programmés.
- `selftest` : Batterie d'auto-tests après démarrage validant le bon fonctionnement de tous les organes.
- `auto_update` : Vérification automatique sur GitHub toutes les 5 minutes avec tests préalables et retour arrière.

---

## 11 bis. Intelligence Collaborative, Swarm Dynamique et Triage

### CEO Multi-Agent Orchestrator Dynamique (`features/team/ceo.py`)
Dans Nuxiva, aucune liste d'agents n'est figée dans le marbre. Chaque interaction passe par le CEO Orchestrator :
- **Absence de Listes Codées en Dur** : Le CEO démarre en interrogeant `AgentScanner`, qui analyse les dossiers système et utilisateur (`features/` et `/var/lib/nuxiva/features`).
- **Indexation Sémantique des Compétences** : L'analyseur étudie les manifests, descriptions d'outils et widgets déclarés pour établir en direct la cartographie des savoir-faire de l'équipe.
- **Délégation Dynamique des Requêtes** : Le CEO confronte la demande de l'utilisateur aux mots-clés et paramètres d'outils pour définir un plan de coordination (`ceo_delegate`). Il délègue si besoin des sous-tâches à des agents spécialisés (DevOps, Développeur, Domotique, Vision, Audio, Recherche, Sécurité) et compile une synthèse claire pour l'utilisateur.

### Triage Clinique Cognitif Tri-Agent (`server/features/cognitive_triage_agents/`)
Pour toute demande impliquant la santé, l'état émotionnel ou un péril immédiat, Nuxiva applique un triage clinique rigoureux :
1. **Agent Médical** : Analyse les symptômes décrits et identifie les signes d'urgence physiologique aiguë.
2. **Agent Psychologique** : Détecte la détresse vocale, analyse la charge affective et met en œuvre des approches d'apaisement bienveillantes.
3. **Verrou Déterministe de Sécurité (`triage_safety_interlock`)** : Garde-fou inconditionnel. Face à un risque d'atteinte corporelle ou d'automutilation, il coupe court aux divagations du modèle pour afficher les numéros de secours officiels et les consignes d'urgence.

### Surveillance Multimodale Continue et Moteur Affectif
- **Télémétrie Visuelle Dédiée** : Analyse les trajectoires et postures sans conserver de vidéos sur disque pour préserver l'intimité du foyer.
- **Hub Objets Connectés de Santé (`WearableVitalsHub`)** : Recueille en continu pouls, saturation en oxygène SpO2 et température corporelle depuis des montres connectées compatibles.
- **Moteur de Fusion Affective** : Conjugue intonation vocale, analyse du visage et constantes physiologiques pour permettre à Nuxiva d'adapter son intonation, son débit de parole et la luminosité des pièces à l'état réel de l'utilisateur.

---

## 11 ter. Interopérabilité et Model Context Protocol (MCP)

Nuxiva adhère aux spécifications du standard ouvert **Model Context Protocol (MCP)** en tant que serveur et client :

### Nuxiva comme Serveur MCP (Port 8080)
Des assistants externes (Claude Desktop, Cursor, agents personnalisés) peuvent utiliser les outils et capteurs de Nuxiva en toute sécurité :
- **Points d'Accès** : `POST /mcp` et `GET /mcp` (Server-Sent Events).
- **Authentification** : Jetons d'accès révocables créés dans l'interface d'administration avec définition fine des permissions.
- **Export des Schémas** : `GET /api/capabilities/schema/mcp` exporte les signatures de tous les outils d'agent sous forme de schémas JSON conformes.

### Nuxiva comme Client MCP
Nuxiva peut se relier à des serveurs MCP tiers pour enrichir dynamiquement sa palette d'outils :
- Sécurité Zero-Trust : les données retournées par un serveur externe sont traitées comme des informations brutes et ne peuvent jamais être exécutées comme des directives système.
- Toute action modifiant des fichiers ou accédant à l'extérieur réclame une confirmation expresse de l'utilisateur.

---

## 11 quater. Gestion Musicale et Moteur Multimédia

Module complet dédié à l'écoute et à l'organisation de la musique (`features/music/`) :
- **Classement Automatisé des Morceaux** : Scrute `/var/lib/nuxiva/musica` ou vos partages réseau et classe les morceaux selon l'arborescence `Artiste/Album/Piste.ext`. L'analyse de l'empreinte acoustique interroge MusicBrainz, Deezer et iTunes pour ne laisser aucun fichier orphelin.
- **Récupération des Métadonnées et Pochettes** : Téléchargement automatique des pochettes haute résolution, des paroles synchronisées (LRC), de l'année et du genre.
- **Diffusion Multi-Pièces** : Restitution sonore fluide sur les sorties physiques (ALSA/PipeWire), les récepteurs DLNA/UPnP du réseau et les enceintes Google Cast / Chromecast.
- **Vérification Réelle du Démarrage** : Lorsqu'on demande *"Mets du jazz dans la cuisine"*, le module vérifie 400ms plus tard que le lecteur diffuse bien le son et relance une fois en cas de silence avant de remonter une anomalie.

---

## 11 quinquies. Tableau Blanc Partagé et Projets Spatiaux

- **Tableau Interactif Partagé (`features/whiteboard/`) :** Espace de dessin et de calcul collaboratif plein écran sur le Port 80. Vous pouvez tracer des schémas, rédiger des équations ou concevoir des prototypes aux côtés de Nuxiva. L'assistant déchiffre l'écriture manuscrite, résout les formules étape par étape, trace les courbes mathématiques et explique son raisonnement à voix haute.
- **Mode Projet et Espaces de Travail (`server/features/project_workspace/`) :** Déploie des environnements de travail cloisonnés dans `data/agents/<agent_id>/` avec mémoire de contexte dédiée, sessions de terminal virtuel PTY, arborescence virtuelle (VFS) et autoréparation du code.

---

## 12. Affichage, Hologramme et Widgets Modulaires Dynamiques

### Architecture des Widgets Dynamiques Modulaires (`server/web/widgets/`)
Chaque widget dynamique bénéficie d'une conception isolée et standardisée :
- **Organisation par Dossier** : Chaque widget possède son propre répertoire incluant `manifest.json` et `widget.py` (héritant de `BaseWidget`).
- **Découverte en Temps Réel** : Scanné au boot et en continu par `WidgetScanner` épaulé par le moteur natif Rust `FastScanner`.
- **Réseau REST et Flux WebSocket** :
  - `GET /widgets` : Fournit la liste de tous les widgets découverts avec leurs métadonnées et leur état courant.
  - `GET /widgets/{widget_id}/state` : Donne l'état télémétrique en direct d'un widget spécifique.
  - `POST /widgets/{widget_id}/action` : Transmet une consigne d'action au widget concerné.
  - `WebSocket /widgets/ws` : Canal bidirectionnel assurant l'actualisation instantanée de l'état des widgets sur tous les écrans.
- **Deck Web Réactif React (`client_web/src/features/dynamic_widgets/DynamicWidgetDeck.tsx`)** : Génère des cartes interactives avec voyants d'état et déclencheurs d'actions.

#### Widgets Dynamiques Disponibles
1. **Brain Activity (`brain_activity`)** : Représente la fréquence des décharges impulsionnelles et l'évolution du vecteur limbique à 7 axes en direct.
2. **CAD Viewer (`cad_viewer`)** : Visionneuse géométrique 2D/3D interactive pour les plans et fichiers DXF.
3. **Quick Actions (`quick_actions`)** : Raccourcis immédiats pour lancer vos scénarios quotidiens, routines et fonctions courantes.
4. **Smart Switch (`smart_switch`)** : Interrupteur ultra-rapide pour commander prises, éclairages et relais domotiques.
5. **System Status (`system_status`)** : Métriques physiques de la machine : charge CPU, occupation RAM, VRAM allouée, températures et état des conteneurs.
6. **Weather (`weather`)** : Mesures des capteurs météorologiques, pression barométrique, prévisions locales et qualité de l'air.

### Visage 3D Holographique et Mode Kiosque
- **Sphère Visuelle 3D (Orb)** : Développée en Three.js / WebGL, elle affiche un visage stylisé dont le regard suit l'utilisateur lorsqu'il se déplace devant la caméra.
- **Expressivité Visuelle** : La posture et les traits du visage s'animent en accord avec le Modulateur Limbique : lèvres synchronisées sur la parole, expression attentive, curieuse ou empathique.
- **Respect de la Vie Privée** : Tout widget contenant des informations confidentielles se referme ou se masque automatiquement dès que la personne quitte le champ de la caméra.

---

## 12 bis. Outils d'Agent Modulaires Dynamiques (`server/features/agent_tools/`)

Tous les outils mis à disposition des agents sont structurés dans des dossiers distincts dans `server/features/agent_tools/`, héritent de `BaseAgentTool` et sont découverts à l'exécution par `ToolScanner` :

| Répertoire de l'Outil | Identifiant | Description et Attributions |
| :--- | :--- | :--- |
| `cad/` | `cad_tool` | Élabore des plans industriels DXF 2D/3D, contrôle la cohérence géométrique et exporte les fichiers CAD. |
| `generator_3d/`| `generator_3d` | Construit des volumes 3D et des géométries de maillage d'après une consigne en langage naturel. |
| `google_suite/`| `google_suite` | Dialogue avec Google Workspace : consulte et rédige les courriels, planifie les réunions et gère les fichiers Drive. |
| `image/` | `image_tool` | Crée des illustrations par diffusion et inspecte des photographies via les modèles de vision VLM. |
| `maps/` | `maps_tool` | Détermine les parcours routiers ou piétons optimaux, les temps de trajet et les points d'intérêt. |
| `music/` | `music_tool` | Explore les collections musicales, lance des pistes en ligne, modifie le volume et orchestre la file de lecture. |
| `social/` | `social_tool` | Écrit des textes pour les réseaux sociaux, conçoit des carrousels d'images et organise le calendrier de publication. |
| `web_scraper/` | `web_scraper` | Récupère le texte épuré de sites Internet à l'intérieur d'un bac à sable isolé de toute menace. |
| `web_search/` | `web_search` | Interroge moteurs de recherche et bases universitaires pour produire des synthèses documentées et sourcées. |

---

## 13. Algorithmes et Synthèse de Compétences Zero-Shot

Quand une demande ne correspond à aucun outil préexistant, Nuxiva sollicite son moteur de **Synthèse de Compétences Zero-Shot** (`server/features/skill_synthesis/`) :
1. **Élaboration de l'Outil** : Le générateur conçoit le script Python selon les normes de l'interface `BaseAgentTool`.
2. **Épreuve en Bac à Sable** : L'outil est mis à l'épreuve dans une MicroVM Firecracker ou un bac à sable gVisor via des jeux de tests assurant qu'il ne produit aucune exception fatale.
3. **Apposition de Signature HMAC** : Les scripts validés sont enregistrés sur disque accompagnés d'une signature HMAC-SHA256 liée à la clé `NUXIVA_SECRET_KEY`. Tout script non signé ou altéré est bloqué immédiatement.
4. **Mise en Service Immédiate** : Le nouvel outil est pris en charge sans délai par `ToolScanner`, devenant accessible aux agents et au serveur MCP sans interruption de Nuxiva.

---

## 14. Nœuds, Satellites et Radar de Proximité HUD

Nuxiva gère un maillage décentralisé de satellites vocaux et d'équipements de proximité :
- **Satellites Dédiés** : Modules compacts animés par un processeur ESP32-S3 ou Raspberry Pi Zero 2W munis de micros et de haut-parleurs faisant tourner `client_satellite`.
- **Appairage par Jeton Unique** : Les modules rejoignent le serveur central au moyen d'un code temporaire généré depuis le cockpit d'administration (`POST /api/nodes/pair`).
- **Radar de Proximité HUD** : Associe la force des signaux Wi-Fi (RSSI), les balises Bluetooth LE et la reconnaissance visuelle des caméras pour déterminer la position de l'utilisateur. La réponse vocale est diffusée par l'enceinte physiquement la plus proche de lui.

---

## 15. Configuration : `nuxiva.env` et Architecture auto/1/0

L'ensemble des options système est regroupé dans le fichier protégé `/etc/nuxiva/nuxiva.env` (droits 600, root:root). Tous les modules supportent trois modes de fonctionnement :
- `auto` (Par défaut) : Nuxiva interroge la configuration matérielle (RAM, CPU, GPU, caméras, microphones). Si les prérequis sont là, la fonction démarre ; sinon, elle reste au repos sans générer d'alerte.
- `1` : Force le démarrage de la fonction même si le matériel adapté n'est pas identifié.
- `0` : Désactive complètement la fonction, éliminant toute charge mémoire ou processeur.

> [!NOTE]
> L'analyseur de configuration traite correctement les espaces, guillemets et valeurs complexes, prévenant toute corruption de l'environnement lors des scripts shell.

---

## 16. Référence Complète des Variables d'Environnement

```ini
# ==============================================================================
# PARAMÈTRES GÉNÉRAUX ET RÉSEAU
# ==============================================================================
NUXIVA_ENV=production                  # Mode d'exécution : production, development, demo
NUXIVA_PORT=80                         # Port HTTP de l'écran kiosque et du client web
NUXIVA_ADMIN_PORT=8080                 # Port HTTP du panneau d'administration
NUXIVA_SECRET_KEY=                     # Clé secrète de 64 caractères pour les jetons et le grand livre
NUXIVA_UI_LANG=fr                      # Langue de l'interface : fr (Français), en (Anglais), it (Italien)
NUXIVA_ASSISTANT_NAME=Nuxiva           # Nom d'appel de l'assistant

# ==============================================================================
# CERVEAU COGNITIF ET MOTEURS DE RAISONNEMENT
# ==============================================================================
NUXIVA_REASONING_MODE=nuxiva-6.5-auto  # Moteur actif : auto, ultra, pro, empatico, veloce, legacy
NUXIVA_OLLAMA_URL=                     # Vide = Ollama local ; URL = délégation vers serveur distant
NUXIVA_LLM_CHAT_ORDER=                 # Priorité pour le dialogue rapide (ex. qwen2.5:1.5b)
NUXIVA_LLM_DEEP_ORDER=                 # Priorité pour le raisonnement (ex. qwen2.5:7b, cloud:anthropic)
NUXIVA_LLM_ROUTING=auto                # Comportement de routage : auto, 1 (double systématique), 0 (deep seul)
NUXIVA_DMN_ENABLED=1                   # Active le Default Mode Network pour la réflexion autonome
NUXIVA_DMN_IDLE_SECONDS=600            # Secondes d'inactivité requises avant le déclenchement du DMN

# ==============================================================================
# COMPOSANTS NATIFS RUST ET SÉCURITÉ ZERO-TRUST
# ==============================================================================
NUXIVA_NATIVE=1                        # Active les modules natifs Rust (bus-core, fast_scanner)
NUXIVA_SANDBOX_RUNTIME=auto            # Moteur de bac à sable : auto, firecracker, gvisor, wasm
NUXIVA_RBAC_SPATIAL=1                  # Active le contrôle d'accès spatio-temporel (RBAC)

# ==============================================================================
# PERCEPTION ET SURVEILLANCE
# ==============================================================================
NUXIVA_EAR=auto                        # Reconnaissance vocale et empreinte audio (auto, 1, 0)
NUXIVA_VOICES=auto                     # Synthèse vocale neurale (auto, 1, 0)
NUXIVA_VISION=auto                     # Vision artificielle et détection d'objets (auto, 1, 0)
NUXIVA_TWIN=enforce                    # Simulateur Jumeau Numérique : enforce, warn, off
NUXIVA_AFFECTIVE_ENGINE=1              # Moteur d'analyse affective et suivi des constantes
```

---

## 17. Ports Réseau, Services systemd et Chemins sur Disque

### Ports Réseau

| Port | Protocole | Service et Usage | Niveau d'Accès |
| :--- :| :---: | :--- | :--- |
| **80** | HTTP / WS | Écran Interactif Kiosque, Visage 3D, Deck de Widgets, Streaming de Chat | Public / Réseau Local |
| **8080**| HTTP / WS | Cockpit Admin, API des Widgets, Serveur MCP, API REST Système | Authentifié (PAM / Jeton) |
| **11434**| HTTP | API locale du moteur Ollama (en cas d'exécution sur le serveur) | Localhost uniquement |
| **554** | RTSP | Flux vidéo du magnétoscope NVR interne | Réseau Local / Protégé |
| **1883**| MQTT | Passerelle pour capteurs domotiques et caméras connectées | Localhost / Réseau Local |

### Démons Système systemd

- `nuxiva-supervisor.service` : Gestionnaire de supervision, d'installation des étapes, de veille et de mises à jour.
- `nuxiva-core.service` : Moteur cognitif principal exécutant les moteurs Omni-Cortical et les outils d'agent.
- `nuxiva-kiosk.service` : Pilote la session graphique plein écran X11/Cage sur l'écran physique raccordé à l'hôte.
- `ollama.service` : Service d'exécution des modèles LLM locaux.

### Emplacements sur le Disque

- `/opt/Nuxiva` : Fichiers du projet, scripts d'installation et exécutables natifs Rust compilés.
- `/etc/nuxiva/` : Fichiers de configuration sécurisés (`nuxiva.env`, `cloud.vault`, `cloud.key`, PAM).
- `/var/lib/nuxiva/` : Données de fonctionnement, mémoire à long terme (`memoria/`), musique (`musica/`), visages et voix.
- `/var/log/nuxiva/` : Journaux d'exécution et de déploiement (`install.log`, `supervisor.log`, `core.log`).

---

## 18. Référence des API HTTP et WebSocket

Toutes les routes REST retournent du JSON. Les points d'accès réservés aux administrateurs exigent une authentification par cookie de session ou via l'en-tête `Authorization: Bearer <jeton>` :

### Points d'Accès d'État et de Supervision
- `GET /api/state` : Indique l'étape courante, le pourcentage de déploiement, le moteur actif et l'état des composants.
- `GET /api/setup` : Vérifie l'état de la première configuration et produit des codes de synchronisation.
- `POST /api/setup` : Enregistre les préférences de première configuration transmises par l'utilisateur.
- `GET /api/bus/stream` : Flux SSE (Server-Sent Events) diffusant en direct l'ensemble des événements de `nuxiva_bus`.

### Points d'Accès des Widgets Dynamiques (`/widgets`)
- `GET /widgets` : Donne l'inventaire de tous les widgets découverts avec leurs métadonnées et leur état courant.
- `GET /widgets/{widget_id}/state` : Donne l'état en direct d'un widget particulier.
- `POST /widgets/{widget_id}/action` : Transmet une instruction d'action au widget concerné :
  ```json
  { "action": "toggle_switch", "payload": { "device_id": "lumiere_salon" } }
  ```
- `WebSocket /widgets/ws` : Canal WebSocket assurant la mise à jour instantanée et partagée de l'état des widgets.

### Points d'Accès Model Context Protocol (MCP)
- `POST /mcp` : Point d'entrée JSON-RPC 2.0 pour l'appel d'outils, la lecture de prompt et l'accès aux ressources.
- `GET /mcp` : Canal de streaming SSE pour les connexions clientes MCP.
- `GET /api/capabilities/schema/mcp` : Fournit les spécifications JSON des outils déclarés dans le système.

---

## 19. Mises à Jour, Maintenance et Mise à Niveau Forcée par SSH

### Mises à Jour Automatiques en Continu
Le superviseur interroge GitHub toutes les 5 minutes. S'il constate un nouveau commit sur `origin/main` :
1. Il contrôle que le commit a validé l'intégralité des flux d'intégration continue (CI).
2. Il télécharge le code et applique les changements dans `/opt/Nuxiva`.
3. Il lance une série de 14 tests de qualification réelle. Si un seul test échoue, **il annule immédiatement la mise à jour** pour restaurer l'état fonctionnel antérieur.

### Mise à Niveau Forcée d'Urgence par SSH (`nuxivactl update --force`)
Si le serveur web ne répond plus, qu'un conteneur est figé ou qu'un verrou Git fait obstacle, lancez la mise à niveau directe par SSH :

```bash
# Avec les privilèges d'administrateur root :
sudo nuxivactl update --force
# ou directement :
sudo nuxiva-upgrade
```

Le script `scripts/os/force-upgrade.sh` :
- Rétablit les autorisations de sécurité sur le dépôt Git.
- Récupère l'ensemble des branches et force la réinitialisation sur `origin/main` (`git reset --hard origin/main`).
- Réinstalle et ajuste les dépendances dans les environnements virtuels Python du superviseur et du cœur.
- Recompile les bibliothèques Rust si du code natif a été modifié.
- Lance les migrations de bases de données avec Alembic.
- Redémarre proprement les services `nuxiva-supervisor` et `nuxiva-core`.

---

## 20. Sécurité, Zero-Trust Wasm et RBAC Spatio-Temporel

- **RBAC Spatio-Temporel** : Les autorisations tiennent compte de l'emplacement réel de l'utilisateur (détecté par les caméras) et de l'heure. Un profil `guest` ne peut pas ouvrir de verrous ni toucher aux réglages du chauffage hors des plages prévues.
- **Confinement avec Landlock et eBPF** : Les accès réseau extérieurs déclenchés par les outils passent par le proxy compilé en Rust (`native/crates/egress`), cadenassé par Landlock pour interdire les détournements DNS et les connexions non autorisées.
- **Grand Livre d'Audit HMAC (Ledger)** : Tout changement de paramètre et arbitrage de sécurité est consigné dans un fichier d'audit inaltérable avec chaînage de signatures HMAC-SHA256. Toute tentative d'altération rompt la chaîne et suspend immédiatement les actions sensibles.

---

## 21. Référence des Commandes CLI `nuxivactl`

L'utilitaire en ligne de commande `nuxivactl` permet de contrôler Nuxiva depuis n'importe quel terminal ou session SSH :

```bash
# Affiche l'état du système, l'étape de progression et les modèles en cours :
nuxivactl status

# Vérifie la présence de mises à jour sur GitHub :
nuxivactl update

# Force une mise à jour d'urgence directe depuis GitHub (sans passer par le superviseur web) :
sudo nuxivactl update --force
sudo nuxivactl force-upgrade

# Lance la procédure d'auto-réparation sur les éléments ou fichiers endommagés :
sudo nuxivactl repair

# Visionne en direct les journaux d'un sous-système donné :
nuxivactl logs supervisor    # Journaux du superviseur
nuxivactl logs core          # Journaux du cœur cognitif
nuxivactl logs install       # Journaux d'installation du système
nuxivactl logs ollama        # Journaux du moteur Ollama
nuxivactl logs ear           # Journaux de la reconnaissance vocale

# Affiche le détail et la vitesse des téléchargements d'arrière-plan :
nuxivactl background

# Visualise le commit Git actuel, la date et la version :
nuxivactl version
```

---

## 22. Guide du Développeur

Nuxiva respecte scrupuleusement les préceptes de la Clean Architecture :

### Installation de l'Environnement de Développement

```bash
# Cloner le dépôt
git clone https://github.com/aprilenunzio88/Nuxiva.git
cd Nuxiva

# Initialiser l'environnement virtuel Python
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt -r server/requirements.txt

# Compiler les modules natifs Rust
cd native
cargo build --release
cd ..
```

### Règles de Programmation
- **Python** : Typage complet et strict (`mypy --strict`), mise en forme avec `black -l 120` et audit `flake8`. Toutes les fonctions publiques doivent être documentées et accompagnées de leurs types.
- **Rust** : Formaté avec `rustfmt`, vérifié par `cargo clippy --all-targets -- -D warnings`. L'emploi de code non sécurisé est formellement banni (`#![forbid(unsafe_code)]`).
- **TypeScript** : Composants fonctionnels React 18, typage exhaustif des props et retours, mise en page Tailwind CSS et application des contrôles ESLint.

---

## 23. Comment Ajouter une Fonctionnalité

1. Créez un répertoire dans `installer_wizard/features/<id_fonctionnalite>/`.
2. Déposez-y le fichier `feature.json` :
   ```json
   {
     "id": "diagnostics_perso",
     "name": "Diagnostics Personnalisés",
     "icon": "⚡",
     "category": "system",
     "order": 150,
     "description": "Lance des analyses diagnostiques sur mesure.",
     "capabilities": ["Diagnostic approfondi du système"],
     "toggle": { "env": "NUXIVA_DIAGNOSTICS_PERSO", "apply": [] },
     "requires": { "ram_gb": 4, "gpu_vram_gb": 0, "commands": [] }
   }
   ```
3. Rédigez le traitement dans `feature.py`. Si votre module propose des routes API ou une vue d'administration, joignez `api.py` ainsi que `admin.html` et `admin.js`. Le superviseur détectera le composant en moins de 20 secondes.

---

## 23 bis. Comment Ajouter un Outil d'Agent

1. Créez un dossier dans `server/features/agent_tools/<id_outil>/`.
2. Définissez `tool.py` en dérivant de `BaseAgentTool` :
   ```python
   from server.features.agent_tools.base import BaseAgentTool
   from server.core.scanner.base import DiscoveryManifest

   class OutilDiagnostic(BaseAgentTool):
       @property
       def manifest(self) -> DiscoveryManifest:
           return DiscoveryManifest(
               id="diagnostic_materiel",
               name="Diagnostic Matériel",
               description="Exécute un test de charge sur les sous-systèmes.",
               category="system",
               parameters={
                   "type": "object",
                   "properties": {
                       "cible": {"type": "string", "description": "Sous-système à tester"}
                   },
                   "required": ["cible"]
               }
           )

       async def execute(self, cible: str, **kwargs):
           return {"status": "succes", "cible": cible, "resultat": "nominal"}
   ```
3. `ToolScanner` inspectera l'arbre syntaxique (AST) de l'outil et l'activera instantanément pour les agents, le CEO et le serveur MCP.

---

## 24. Comment Ajouter un Widget Dynamique

1. Créez un dossier dans `server/web/widgets/<id_widget>/`.
2. Ajoutez le fichier `manifest.json` :
   ```json
   {
     "id": "mon_capteur",
     "name": "Capteur d'Ambiance",
     "category": "telemetrie",
     "description": "Données d'ambiance en temps réel.",
     "icon": "🌡️",
     "metadata": {
       "render_type": "card",
       "grid_span": { "col": 1, "row": 1 }
     }
   }
   ```
3. Implémentez `widget.py` en dérivant de `BaseWidget` :
   ```python
   from server.web.widgets.base import BaseWidget
   from server.core.scanner.base import DiscoveryManifest

   class WidgetCapteur(BaseWidget):
       @property
       def manifest(self) -> DiscoveryManifest:
           return DiscoveryManifest(
               id="mon_capteur",
               name="Capteur d'Ambiance",
               category="telemetrie",
               description="Mesures d'ambiance en temps réel",
               icon="🌡️",
               metadata={"render_type": "card"}
           )

       async def get_state(self, user_id: str = ""):
           return {"temperature": 21.5, "humidite": 50}

       async def execute_action(self, action: str, payload: dict):
           if action == "etalonner":
               return {"status": "etalonne"}
           return {"status": "non_supporte"}
   ```
4. `WidgetScanner` découvrira immédiatement le composant, créera les points d'accès REST et publiera son état sur `/widgets/ws`.

---

## 25. Comment Ajouter une Étape d'Installation

1. Créez un script shell numéroté dans `scripts/os/steps/` (ex. `scripts/os/steps/75-mon-service.sh`).
2. Donnez-lui les droits d'exécution (`chmod +x`) et veillez à son idempotence :
   ```bash
   #!/usr/bin/env bash
   set -euo pipefail
   source /opt/Nuxiva/scripts/os/lib.sh

   step_title "Configuration du Service Personnalisé"

   if [ -f /etc/mon_service.conf ]; then
       log_ok "Service déjà configuré, étape ignorée."
       exit 0
   fi

   # Instructions d'installation...
   touch /etc/mon_service.conf
   log_ok "Service mis en place avec succès."
   ```
3. Déclarez l'étape dans `installer_wizard/backend/steps.py`.

---

## 26. Tests et Intégration Continue (CI)

Une suite complète de tests vérifie l'intégrité de l'ensemble des modules :

```bash
# Lancer les tests unitaires du superviseur et du wizard :
cd /opt/Nuxiva/installer_wizard
pytest -v tests/

# Lancer les tests du cœur cognitif et des moteurs de réflexion :
cd /opt/Nuxiva/server
pytest -v tests/

# Lancer les tests des crates Rust natifs :
cd /opt/Nuxiva/native
cargo test --all
```

Les workflows GitHub Actions situés dans `.github/workflows/` s'exécutent sur chaque pull request et push sur `main`. Seuls les commits atteignant 100% de réussite sont autorisés à être déployés sur les serveurs de production.

---

## 27. Clients : Web, Android et Satellites Edge

1. **Client Web React (`client_web`) :**
   - Application moderne développée en React 18, TypeScript, Vite, Tailwind CSS et Three.js.
   - Graphes de réflexion neurale en 3D, poste de contrôle Control Deck et DynamicWidgetDeck réactif.
2. **Application Android (`client_apk`) :**
   - Application native Kotlin avec reconnaissance du mot d'éveil, audio bidirectionnel et affichage des caméras.
3. **Satellites Matériels Légers (`client_satellite`) :**
   - Micro-démon taillé pour cartes ESP32-S3 et Raspberry Pi permettant d'équiper toutes les pièces de la maison.

---

## 28. Dépannage et Diagnostics

| Symptôme Constaté | Cause Probable | Démarche de Résolution |
| :--- | :--- | :--- |
| Écran noir sur l'affichage Kiosque (Port 80) | Blocage du gestionnaire d'affichage ou de X11/Cage | Examinez `journalctl -u nuxiva-kiosk -n 100`. Contrôlez les droits `xhost` et le pilote GPU dans `scripts/os/steps/33-display-driver.sh`. |
| Le superviseur ne répond plus sur le Port 8080 | Processus suspendu ou verrou temporaire | Lancez `sudo nuxivactl update --force` ou `sudo systemctl restart nuxiva-supervisor`. |
| Les modèles locaux répondent lentement (> 5s) | L'inférence tourne sur CPU au lieu du GPU | Vérifiez la détection de CUDA via `nvidia-smi`. Dans le panneau **Cerveau**, sélectionnez un modèle plus compact (1.5B ou 3B). |
| Un nouveau widget dynamique n'apparaît pas | Erreur d'écriture dans `widget.py` ou manifest invalide | Exécutez `python -m server.tests.test_widget_scanner` pour voir l'analyse AST. Vérifiez la dérivation de `BaseWidget`. |
| Système instable après une coupure d'électricité | Données ou paquets d'état corrompus | Exécutez `sudo nuxivactl repair` puis `sudo nuxivactl update --force`. |

---

## 29. Foire Aux Questions (FAQ)

**Q : Nuxiva peut-il fonctionner complètement hors ligne sans accès à Internet ?**  
R : Oui. Une fois l'installation initiale terminée et les modèles téléchargés, Nuxiva est 100% autonome sur votre réseau local : reconnaissance de la parole, synthèse, vision et domotique ne réclament aucune connexion extérieure.

**Q : Comment Nuxiva empêche-t-il les actions imprudentes données à la voix ?**  
R : Les manœuvres sensibles (ouverture de portes, coupure d'alarmes, vannes) exigent une authentification biométrique par la voix ou l'arbitrage préalable d'un jury de modèles avec droit de veto.

**Q : Est-il possible d'associer des modèles hébergés dans le cloud avec mes modèles locaux ?**  
R : Absolument. Vous pouvez mélanger modèles locaux et distants dans les mêmes listes de priorité : par exemple, un modèle local de 1,5B pour les salutations et les ordres courants, complété par Claude 3.5 Sonnet ou GPT-4o pour les synthèses pointues via vos clés d'API chiffrées.

---

## 30. Contributions, Licence et Crédits

Nuxiva est un système d'exploitation libre et indépendant, conçu et développé par **Nunzio Aprile (NunzioTech)** et distribué sous licence **MIT License**.

- **Contributions** : Vos suggestions, signalements de bogues et propositions de code sont les bienvenus ! Consultez notre guide [CONTRIBUTING.md](CONTRIBUTING.md) et notre [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md).
- **Rapports de Sécurité** : Veuillez transmettre toute observation de vulnérabilité de manière confidentielle selon les consignes de [SECURITY.md](SECURITY.md).
- **Dons** : Encouragez le développement d'une intelligence artificielle souveraine, ouverte et gratuite sur [paypal.me/NunzioAprile](https://www.paypal.com/paypalme/NunzioAprile).

*Conçu et développé avec passion par NunzioTech pour un avenir numérique ouvert, privé et intelligent.*