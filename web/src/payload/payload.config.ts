import { buildConfig } from "payload";
import { postgresAdapter } from "@payloadcms/db-postgres";
import { lexicalEditor } from "@payloadcms/richtext-lexical";
import { azureStorage } from "@payloadcms/storage-azure";
import path from "path";
import { fileURLToPath } from "url";

import { Articles } from "./collections/Articles";
import { ActionAlerts } from "./collections/ActionAlerts";
import { Pages } from "./collections/Pages";
import { Media } from "./collections/Media";
import { Users } from "./collections/Users";
import { SiteSettings } from "./collections/SiteSettings";

const filename = fileURLToPath(import.meta.url);
const dirname = path.dirname(filename);

export default buildConfig({
  admin: {
    user: Users.slug,
    meta: {
      titleSuffix: " - Civitas CMS",
    },
  },
  collections: [Articles, ActionAlerts, Pages, Media, Users],
  globals: [SiteSettings],
  editor: lexicalEditor({}),
  secret: process.env.PAYLOAD_SECRET || "CHANGE-ME-IN-PRODUCTION",
  typescript: {
    outputFile: path.resolve(dirname, "payload-types.ts"),
  },
  db: postgresAdapter({
    pool: {
      connectionString: process.env.DATABASE_URL || "",
    },
  }),
  plugins: [
    azureStorage({
      collections: {
        media: {
          disableLocalStorage: true,
          prefix: "media",
        },
      },
      allowContainerCreate: true,
      connectionString: process.env.AZURE_STORAGE_CONNECTION_STRING || "",
      containerName: process.env.AZURE_STORAGE_CONTAINER || "civitas",
      baseURL: `https://${process.env.AZURE_STORAGE_ACCOUNT || "baytidesstorage"}.blob.core.windows.net/${process.env.AZURE_STORAGE_CONTAINER || "civitas"}`,
    }),
  ],
});
