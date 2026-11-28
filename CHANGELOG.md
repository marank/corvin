# Changelog

## 0.1.0 (2026-11-28)


### ⚠ BREAKING CHANGES

* **docker:** rename APP_PORT to APP_BIND in .env, and move the pgdata and media volumes into db-data and app-data (uploads into media/).

### Features

* align environment variables with the shared .env template ([e271209](https://github.com/marank/corvin/commit/e27120974adba6ff4d19fdd1a20ff01f39b4a3b5))
* **attachments:** preview attachments in place ([bed93bb](https://github.com/marank/corvin/commit/bed93bbce9997d04ed127c7c46463afee9cc442a))
* background jobs with procrastinate and a worker ([c15d4e0](https://github.com/marank/corvin/commit/c15d4e0160af35e70e6837e8cd903ee7ccf79752))
* close the remaining design review items ([ef85212](https://github.com/marank/corvin/commit/ef8521267728ef3d200ce77c0bfaff4a786fa88c))
* compact table redesign ([572980a](https://github.com/marank/corvin/commit/572980a6b214d850425342b71c06aeda1b21f377))
* complete Corvin branding and drop the old projectmanager names ([2c765d6](https://github.com/marank/corvin/commit/2c765d6e3e9aad9580fe5ec52c336e306f7ac67b))
* correct numbers by hand until a finalized invoice shows them ([fec2548](https://github.com/marank/corvin/commit/fec2548589630c38e5b66e814d11beacc2f11a63))
* designer preview matches real invoices, mail tab and review fixes ([118ffb1](https://github.com/marank/corvin/commit/118ffb188b724134d185f5c8bde88d096c351198))
* **docker:** data under /data, admin opt-in, checked trusted proxies ([7e67154](https://github.com/marank/corvin/commit/7e67154890c3953fa5d82d8e3cc08ba7f50f128f))
* **docker:** fonts for document templates ([1eaac8a](https://github.com/marank/corvin/commit/1eaac8ab92b3526d1e52b8885ddeee1a3a17be05))
* editable invoice drafts and entry selection in the invoice wizard ([9ebbf6a](https://github.com/marank/corvin/commit/9ebbf6a5e8b2fe0f33d6a6d0ca6693877d5ce5c1))
* filters, overviews, editable contracts and review fixes across the app ([f07550b](https://github.com/marank/corvin/commit/f07550bbc6f4b3f021c475365bf2fe90cfc7e26d))
* **frontend:** tabs live in the URL ([96454ff](https://github.com/marank/corvin/commit/96454ff6a23e73de6bf3d34b77854fda2db163c4))
* harden security settings, add ops services and CI tooling ([166ce98](https://github.com/marank/corvin/commit/166ce9868f2fbb3d08d38cfcc312b906705899d5))
* **invoices:** activity report with the time entries' reports ([898330d](https://github.com/marank/corvin/commit/898330d0573af94b2d29b65d4185b29213f8fd02))
* **invoices:** documents dropdown, ⋮ menu and a sending date ([4d564c8](https://github.com/marank/corvin/commit/4d564c82d5dc5b17f506f4630001d7dfe4d35ad2))
* **invoices:** edit drafts on the create page ([3e4dab6](https://github.com/marank/corvin/commit/3e4dab60dd487504e8461f274d6a7da59e150b96))
* **invoices:** rebuild invoice creation around sections and editable lines ([0c1e61d](https://github.com/marank/corvin/commit/0c1e61dd87bfd730b62ed05104462021e0a2f809))
* **invoices:** rebuild the detail page; invoices list the entries they bill ([91c23cf](https://github.com/marank/corvin/commit/91c23cf1503508a535159cb28d20c28b695fdd8f))
* **invoices:** send history and external invoices ([8f1358f](https://github.com/marank/corvin/commit/8f1358f80326f9c38922350a8b93119f758594b8))
* **mail:** several recipients, greeted by name in the templates ([9b3bdb4](https://github.com/marank/corvin/commit/9b3bdb43e31935b99bd776984447d66f251e1ac9))
* page margins frame the whole page; header/footer heights, page numbers ([257b5ac](https://github.com/marank/corvin/commit/257b5ac4183fd853a3c4e4bf9557db9d320f32c9))
* rebrand app as Corvin with logo, favicon and blue theme ([384bb39](https://github.com/marank/corvin/commit/384bb39a4a3433b725ff06e4082c747f82410b1b))
* steadier tables with a column chooser; Markdown reports ([4185649](https://github.com/marank/corvin/commit/418564939ec1013c339addda4f1313a85c00d372))
* switch the wordmark to Space Grotesk ([be80afd](https://github.com/marank/corvin/commit/be80afd4dd65896fc5fc3e87b9de491a1dde13df))
* **tables:** free or fitted column widths, optional columns ([7b8ceaa](https://github.com/marank/corvin/commit/7b8ceaa668dd27833577417b326fdf02d168e9e8))
* **tables:** one simple rule for column widths ([cb76acf](https://github.com/marank/corvin/commit/cb76acfeda911b8d16b67026320be9fd0dc19208))
* **templates:** e-mail templates, Belegvorlagen and payment reminders ([9194a8b](https://github.com/marank/corvin/commit/9194a8bdd44a2aea91fe426265fbd56db4c14cbf))
* the first APP_URLS entry is the public address ([b358839](https://github.com/marank/corvin/commit/b35883958192a282ad08c6168f681d443acece4a))
* **time:** link time entries to the invoice that bills them ([1511b6b](https://github.com/marank/corvin/commit/1511b6be4c73bb2979d4773303a5ae8fe534f3bb))
* timer start dialog, shared stop flow and filters in time tracking ([c5b2293](https://github.com/marank/corvin/commit/c5b229365a0d1e485a14a757c7c17792e012368b))
* type dates, times and durations instead of clicking ([7e854cd](https://github.com/marank/corvin/commit/7e854cd6e9d155cae74a8d632c237e69109cc251))
* **ui:** Lucide icons throughout ([b74ebc6](https://github.com/marank/corvin/commit/b74ebc66fcbbc8467756b86af59e1fc91088b2d9))
* **ui:** segmented control, sidebar from 56rem ([0c5b76a](https://github.com/marank/corvin/commit/0c5b76a3305aeb7bcca935c35954608fa3663184))
* **visits:** link time entries to on-site visits ([afd4d14](https://github.com/marank/corvin/commit/afd4d14b418158e09cd8667439233b3ac7853ed8))
* **visits:** travel costs for on-site visits ([7f2c8aa](https://github.com/marank/corvin/commit/7f2c8aa59ae61efbf5d1ac420b90c1eaa835f0f4))


### Bug Fixes

* bugs and gaps found in a full click-through ([f4c0eae](https://github.com/marank/corvin/commit/f4c0eae69dd81a75b0412cf457aecf6755e78e51))
* bugs found in the frontend design review ([6ad12bf](https://github.com/marank/corvin/commit/6ad12bff105125e2c0a9209500df635b222dee79))
* **ci:** set the coverage floor to what CI measures ([0c6f76e](https://github.com/marank/corvin/commit/0c6f76e8f8914da5e4564459bdfad3cb0baa7efa))
* dark backdrop on the login page ([7a7b715](https://github.com/marank/corvin/commit/7a7b71583f6cbe67262b946b4b62b35e9754a9f9))
* designer number fields no longer overflow their column ([fa0aa5f](https://github.com/marank/corvin/commit/fa0aa5f102e90949f06462563719dc62a9d6455b))
* **docker:** pass the Host header with its port to Django ([2940120](https://github.com/marank/corvin/commit/2940120bb61e44758bb846114c7291ea1a94d01f))
* drop the unlabeled select-all box from multi-selects ([189a3ed](https://github.com/marank/corvin/commit/189a3ed34de1ba11da9fd1a22daa25ebd1998115))
* **frontend:** count the header in a text column's width ([9a2643d](https://github.com/marank/corvin/commit/9a2643d3e46ba7927523621b50842d5373bcf1f2))
* **frontend:** fit the customer address and contact tables ([234c118](https://github.com/marank/corvin/commit/234c118f58f42d2dca4e0f09a23a09518010e290))
* **frontend:** keep the settings header height across tabs ([5ad3914](https://github.com/marank/corvin/commit/5ad391447a3b4817f585e6a2d3cc056677a3e0b1))
* **frontend:** lay table columns out by their content ([7d79f11](https://github.com/marank/corvin/commit/7d79f11ce916f8c3f4581b994e036e86ee17bf98))
* **frontend:** narrow address roles, unwrap text column headers ([6a8b697](https://github.com/marank/corvin/commit/6a8b69787b230465120efa1f2a119655ca791898))
* **frontend:** reset dialog forms when they open ([c27b91a](https://github.com/marank/corvin/commit/c27b91a5023edc10ec76be23be76787b2d3ae48a))
* **frontend:** shorten the locked number hint ([ed98e4f](https://github.com/marank/corvin/commit/ed98e4f496d6bb1df480f9e17798b5c5f423083c))
* load the company settings once for all stores ([b5d64a5](https://github.com/marank/corvin/commit/b5d64a5fdb4bfd1173ea164dac22534e00d64e92))
* safe and multi-page document rendering ([43dbee1](https://github.com/marank/corvin/commit/43dbee11647e191af684a757522dd1042b4c7428))
* say which background each logo and icon is for ([0ccac08](https://github.com/marank/corvin/commit/0ccac08bfedb07b257ac5264b3b30a5acf0c312c))
* send only finalized invoices by email ([65a3687](https://github.com/marank/corvin/commit/65a3687520cbf1f90ecda2bf85fcfa80f5972cc3))
* serve image and attachment URLs relative to the page ([d40b863](https://github.com/marank/corvin/commit/d40b8631b621d40d48e47eab554c2cc6522825fe))
* serve uploads via authenticated endpoints and harden auth/Docker build ([5a72c06](https://github.com/marank/corvin/commit/5a72c06d5a605297149c9034bbc57f807592d63a))
* **templates:** preview page as wide as the PDF ([fdcc361](https://github.com/marank/corvin/commit/fdcc361f06901f22a2150b29d2832715873ec036))
* the last document template can't be deleted ([54fb353](https://github.com/marank/corvin/commit/54fb35375ee00e4b186777ba1a2256506a044afa))


### Dependencies

* pin minimatch and glob to their fixed versions ([69463a5](https://github.com/marank/corvin/commit/69463a50dab23a4dd0f281ca41e9ad8010c1aab7))
* update backend and frontend packages ([9fde10f](https://github.com/marank/corvin/commit/9fde10f9abd82d82d2927808ee54e5f60e3fa309))


### Documentation

* README for users, contributing, security and operations docs ([d932844](https://github.com/marank/corvin/commit/d932844b45cb767806e21110f66da45ed7add4ba))
* rework the comments in compose.yml and .env.example ([6cdb60c](https://github.com/marank/corvin/commit/6cdb60c55decf3890d18bb69f7de51fde2e700fc))
* working rules for contributors and agents ([2d375c8](https://github.com/marank/corvin/commit/2d375c8d3f70731cac38e414b369c7d182adba80))
