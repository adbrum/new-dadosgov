/**
 * Static application configuration.
 * Values migrated from nuxt.config.ts runtimeConfig.public that do not change per environment.
 */

export const siteConfig = {
  name: "dados.gov.pt",
  title: "dados.gov.pt",
  description:
    "Plataforma aberta de dados públicos portugueses: descarregue, partilhe e reutilize os dados abertos do Estado e das autarquias",
  locale: "pt",
  url: "https://dados.gov.pt",
} as const;

export const uiConfig = {
  searchDebounce: 300,
  qualityDescriptionLength: 100,
  maxJsonPreviewCharSize: 1_000_000,
  maxPdfPreviewByteSize: 10_000_000,
  maxXmlPreviewCharSize: 100_000,
  maxNumberOfResourcesToUploadInParallel: 3,
  resourceFileUploadChunk: 2_000_000,
  maxSortableFiles: 50,
  maxNumberOfDatasetsForDataserviceUpdate: 200,
} as const;

export const licenses = {
  "Autoridades administrativas": [
    { value: "lov2", recommended: true, code: "etalab-2.0" },
    {
      value: "odc-odbl",
      description: "Licença com obrigação de partilha nos mesmos termos",
      code: "ODbL-1.0",
    },
    {
      value: "notspecified",
      description:
        "Aplica-se o regime jurídico de acesso à informação administrativa",
    },
  ],
  "Todos os produtores": [
    { value: "lov2", recommended: true },
    { value: "cc-by", code: "CC-BY" },
    { value: "cc-by-sa", code: "CC-BY-SA" },
    { value: "cc-zero", code: "CC0-1.0" },
    { value: "fr-lo", code: "etalab-2.0" },
    { value: "odc-by", code: "ODC-By-1.0" },
    { value: "odc-odbl", code: "ODbL-1.0" },
    { value: "odc-pddl", code: "PDDL-1.0" },
    { value: "other-at" },
    { value: "other-open" },
    { value: "other-pd" },
    { value: "notspecified" },
  ],
} as const;

export const datasetBadges = ["spd", "inspire", "hvd", "sl", "sr"] as const;

export const guidesConfig = {
  guidesUrl: "https://guides.data.gouv.fr/", // TODO: Replace with PT URL
  guidesCreateAccount:
    "https://guides.data.gouv.fr/publier-des-donnees/guide-data.gouv.fr/creer-un-compte-utilisateur-et-rejoindre-une-organisation", // TODO: Replace with PT URL
  guidesHarvestingUrl:
    "https://guides.data.gouv.fr/guide-data.gouv.fr/moissonnage", // TODO: Replace with PT URL
  guidesCommunityResources:
    "https://guides.data.gouv.fr/publier-des-donnees/guide-data.gouv.fr/ressource-communautaire", // TODO: Replace with PT URL
  apiDocExternalLink:
    "https://guides.data.gouv.fr/publier-des-donnees/guide-data.gouv.fr/api/reference", // TODO: Replace with PT URL
  guideDatasets:
    "https://guides.data.gouv.fr/guide-data.gouv.fr/jeux-de-donnees", // TODO: Replace with PT URL
  guideReuses:
    "https://guides.data.gouv.fr/guide-data.gouv.fr/reutilisations", // TODO: Replace with PT URL
  guideDataservices: "https://guides.data.gouv.fr/guide-data.gouv.fr/api", // TODO: Replace with PT URL
  datasetPublishingGuideUrl:
    "https://guides.data.gouv.fr/publier-des-donnees/guide-qualite/ameliorer-la-qualite-dun-jeu-de-donnees-en-continu/ameliorer-le-score-de-qualite-des-metadonnees", // TODO: Replace with PT URL
  datasetQualityGuideUrl:
    "https://guides.data.gouv.fr/guides-open-data/guide-qualite/ameliorer-la-qualite-dun-jeu-de-donnees-en-continu/ameliorer-le-score-de-qualite-des-metadonnees", // TODO: Replace with PT URL
  datasetRestrictedGuideUrl:
    "https://guides.data.gouv.fr/guides-open-data/guide-juridique/producteurs-de-donnees/quelles-sont-les-obligations", // TODO: Replace with PT URL
  reuseGuideUrl:
    "https://guides.data.gouv.fr/publier-des-donnees/guide-data.gouv.fr/reutilisations", // TODO: Replace with PT URL
  supportUrl: "https://support.data.gouv.fr/", // TODO: Replace with PT URL
  catalogUrl:
    "https://guides.data.gouv.fr/autres-ressources-utiles/catalogage-de-donnees-grist", // TODO: Replace with PT URL
} as const;

export const homepageConfig = {
  publishDatasetOnboarding: "/productores",
  publishReuseOnboarding: "/reutilizadores",
  aboutUs: "/sobre",
  heroImages: [
    "hero_1.png",
    "hero_2.png",
    "hero_3.png",
    "hero_4.png",
    "hero_5.png",
    "hero_6.png",
    "hero_7.png",
    "hero_8.png",
    "hero_9.png",
    "hero_10.png",
    "hero_11.png",
    "hero_12.png",
    "hero_13.png",
    "hero_14.png",
    "hero_15.png",
  ],
} as const;

export const externalServicesConfig = {
  metricsApi: "https://metric-api.data.gouv.fr", // TODO: Replace with PT URL
  metricsSince: "2022-07-01",
  schemaValidataUrl: "https://validata.fr", // TODO: Replace with PT URL
  tabularApiUrl: "https://tabular-api.data.gouv.fr", // TODO: Replace with PT URL
  schemaPublishingUrl: "https://publier.etalab.studio/fr", // TODO: Replace with PT URL
  schemasSite: {
    url: "https://schema.data.gouv.fr/",
    name: "schema.data.gouv.fr",
  }, // TODO: Replace with PT URL
  forumUrl: "https://forum.data.gouv.fr/", // TODO: Replace with PT URL
  newsletterSubscriptionUrl: "https://qvo970cr.sibpages.com/", // TODO: Replace with PT URL
} as const;

export const feedbackConfig = {
  dataSearchFeedbackFormUrl: "https://tally.so/r/mDKv1N", // TODO: Replace with PT URL
  generateShortDescriptionFeedbackUrl: "https://tally.so/r/wbbRxo", // TODO: Replace with PT URL
  generateTagsFeedbackUrl: "https://tally.so/r/w80JNP", // TODO: Replace with PT URL
  publishingDatasetFeedbackUrl: "https://tally.so/r/nGo0yO", // TODO: Replace with PT URL
  publishingDataserviceFeedbackUrl: "https://tally.so/r/w2J7lL", // TODO: Replace with PT URL
  publishingReuseFeedbackUrl: "https://tally.so/r/mV98y6", // TODO: Replace with PT URL
  publishingHarvesterFeedbackUrl: "https://tally.so/r/3NMLOQ", // TODO: Replace with PT URL
} as const;

export const authConfig = {
  changeEmailPage: "change-email",
  changePasswordPage: "change",
  proconnect: {
    homepage: "https://agentconnect.gouv.fr/", // TODO: Replace with PT URL
  },
} as const;

export const harvesterConfig = {
  harvesterPreviewMaxItems: 20,
  harvestEnableManualRun: false,
  harvestBackendsForHidingQuality: ["CSW-ISO-19139"],
  harvesterRequestValidationUrl:
    "https://support.data.gouv.fr/help/datagouv/moissonnage#support-tree", // TODO: Replace with PT URL
} as const;
