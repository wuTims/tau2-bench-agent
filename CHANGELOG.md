# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## 0.1.0 (2026-01-15)


### Features

* **a2a:** add connect timeout to A2A client config ([6bde3fc](https://github.com/wuTims/tau2-bench-agent/commit/6bde3fcf8576c6c9ffb2cbca883e243c906ec34c))
* **a2a:** add deployment scripts for GCP Cloud Run ([51ab3d1](https://github.com/wuTims/tau2-bench-agent/commit/51ab3d16fbd95475617ea1120885bef9373e6d11))
* **a2a:** add Docker and Cloud Run deployment configs ([3d58d3e](https://github.com/wuTims/tau2-bench-agent/commit/3d58d3ec30a30dc244105aedcb3ed9161031249b))
* **a2a:** add evaluation store with filesystem persistence ([7d609ef](https://github.com/wuTims/tau2-bench-agent/commit/7d609ef9c9e2e973adff000e0be17fdd6adaa8b3))
* **a2a:** add GCP Cloud Run deployment with credentials middleware ([c2a6554](https://github.com/wuTims/tau2-bench-agent/commit/c2a6554e45addac41a4d15924a6fff2fca115796))
* **a2a:** add simulation data models for metrics emission ([8f50765](https://github.com/wuTims/tau2-bench-agent/commit/8f50765ca8ac96ce37f4f46f46326df548a182fe))
* **a2a:** add SSE parser utility for stream processing ([62cfa3b](https://github.com/wuTims/tau2-bench-agent/commit/62cfa3b9bf941958806753e2f1f9e40f78328359))
* **a2a:** add SSE progress events to run_tau2_evaluation ([78c3f1e](https://github.com/wuTims/tau2-bench-agent/commit/78c3f1e48173b4084eaaf4d32698fff9d794073c))
* **a2a:** add streaming events module ([984bb5a](https://github.com/wuTims/tau2-bench-agent/commit/984bb5aef30e4c3318e961c795ab8803ff525bfe))
* **a2a:** add system context formatting for A2A agent messages ([0c398ab](https://github.com/wuTims/tau2-bench-agent/commit/0c398ab7585c7784a7a70fd88b6b895806db8e5a))
* **a2a:** add utility module for message compaction and float sanitization ([167d0de](https://github.com/wuTims/tau2-bench-agent/commit/167d0de4dd8729442d0a033edf4c346c48169681))
* **a2a:** enable streaming capability in agent config ([b85547d](https://github.com/wuTims/tau2-bench-agent/commit/b85547d5ab4ba7d23adab8be3f48cc8c7bd906c5))
* add A2A agent CLI arguments and runtime configuration ([e470b78](https://github.com/wuTims/tau2-bench-agent/commit/e470b78ed18d015e081ce925bd3de39b93326c97))
* add A2A protocol client for remote agent evaluation ([3a9ef8f](https://github.com/wuTims/tau2-bench-agent/commit/3a9ef8f07b4300e4e05ae3995aadf314432cc8e1))
* Add comprehensive changelog and automated release management system ([#58](https://github.com/wuTims/tau2-bench-agent/issues/58)) ([f8de30c](https://github.com/wuTims/tau2-bench-agent/commit/f8de30c298689cbe0117d76a378e7315a17e5bd8))
* add datadog experiments with deployment configs ([7a5f0b0](https://github.com/wuTims/tau2-bench-agent/commit/7a5f0b039a5ad04400297a2624edc2e5619f4b3c))
* add Docker deployment configuration ([9a88eac](https://github.com/wuTims/tau2-bench-agent/commit/9a88eac38373c1fe87581c703fb9973e96560f89))
* add Google ADK agent exposing tau2-bench via A2A ([56727fb](https://github.com/wuTims/tau2-bench-agent/commit/56727fb396df29739527275a25c951cfafc35f3c))
* add model-agnostic tool support in tau2_agent ([2576eaa](https://github.com/wuTims/tau2-bench-agent/commit/2576eaa76151078c29718647a592225490e4db70))
* add platform simulation script for A2A evaluation ([7a9be7e](https://github.com/wuTims/tau2-bench-agent/commit/7a9be7e71d4d58d0ddfcee4bb956fa52df211c47))
* add simple Nebius agent for local A2A testing ([5d9d829](https://github.com/wuTims/tau2-bench-agent/commit/5d9d829b8c36be3494a4768d045c4711f4c05e36))
* add task_ids parameter to run_tau2_evaluation tool ([c3f2f1c](https://github.com/wuTims/tau2-bench-agent/commit/c3f2f1c3da326b7cd51da4a744984c96c6e57ebe))
* add tracing module for datadog integration ([71eaedd](https://github.com/wuTims/tau2-bench-agent/commit/71eaedd8484a7c97519322df84d131fee86128fc))
* **agents:** add AGENTBEATS_MODE for root agent card discovery ([95772ac](https://github.com/wuTims/tau2-bench-agent/commit/95772acf8a0a2130a12dcc44222ace4eba191bc7))
* **agents:** add LiteLLM model support and dynamic URL configuration ([b11b729](https://github.com/wuTims/tau2-bench-agent/commit/b11b729ebe7e5f8b4594aab3cc769d9ca7bd9607))
* **agents:** add RootA2AMiddleware for root-based discovery ([7e00b37](https://github.com/wuTims/tau2-bench-agent/commit/7e00b37c5edff58411d4c71e167adeb9966dca0b))
* **agents:** add simple_gemini and kimi_litellm mock agents ([8769822](https://github.com/wuTims/tau2-bench-agent/commit/87698223b2678508bba1cd458e5d19da8eb52f66))
* **ci:** add linux/arm64 platform support for local dev ([09854f4](https://github.com/wuTims/tau2-bench-agent/commit/09854f43e42d49da541007c2cd477b590fd01be3))
* **ci:** add multi-registry Docker publish workflow ([849d7d3](https://github.com/wuTims/tau2-bench-agent/commit/849d7d3585315b1d0138df51400982742de1b555))
* **datadog:** add task efficiency and simulator metrics ([f5f8ba8](https://github.com/wuTims/tau2-bench-agent/commit/f5f8ba83ceae0b9db5422a1754dc36ca5727c7bc))
* **eval:** normalize difficulty against fixed domain baseline ([bcb6765](https://github.com/wuTims/tau2-bench-agent/commit/bcb676513515b8f4d98d0d82ec90a2e684617dd3))
* **experiment:** Add hyperparam sweep experimental code ([#77](https://github.com/wuTims/tau2-bench-agent/issues/77)) ([558e6cd](https://github.com/wuTims/tau2-bench-agent/commit/558e6cd066d7bf05db587fa2dc1509765c7d03bc))
* **gcp:** add Datadog LLMObs to Cloud Run deployment ([58e0e5e](https://github.com/wuTims/tau2-bench-agent/commit/58e0e5e4cb69c0a0d7087b6f3035e120662ce1c9))
* **gym:** add Gymnasium-compatible interface for RL training ([0ed2fd8](https://github.com/wuTims/tau2-bench-agent/commit/0ed2fd8d830a20657d89ae9c2efcc94838aa7129))
* **llm:** add custom model registration for cost tracking ([2620703](https://github.com/wuTims/tau2-bench-agent/commit/262070399adcb5822a02004619778b37ed1db5b5))
* **shared_utils:** add async file I/O with aiofiles ([8112b6a](https://github.com/wuTims/tau2-bench-agent/commit/8112b6a2cb40b8ab5a431c08de1c187ab7bf7c7e))
* support multiple A2A response formats in client ([ae7647c](https://github.com/wuTims/tau2-bench-agent/commit/ae7647c6903ff31733fcd8d875e30e56e9cd30bd))
* **tau2_agent:** accept any participant name in green executor ([27f3b3b](https://github.com/wuTims/tau2-bench-agent/commit/27f3b3b874c927856b5c50c6c2578fd390b142e8))
* **tau2_agent:** add domain, num_trials, and difficulty metrics to evaluation output ([0faef9a](https://github.com/wuTims/tau2-bench-agent/commit/0faef9aea6f6094ad36a341d70b45ce7c744a4a7))
* **tau2_agent:** add GreenExecutor for AgentBeats DataPart results ([5f85211](https://github.com/wuTims/tau2-bench-agent/commit/5f852112d83311b68e48fb0c1eef791de15d87f4))
* **tau2_agent:** add provider-aware API key resolution ([cb328bf](https://github.com/wuTims/tau2-bench-agent/commit/cb328bf44441b55220e8a068fc8e749c241db159))
* **tau2_agent:** add structured logging and observability modules ([34ac421](https://github.com/wuTims/tau2-bench-agent/commit/34ac421df847aa15d4b09f0001fbdc1e78fba964))
* **tau2_agent:** add task_split parameter to evaluation tool ([930c056](https://github.com/wuTims/tau2-bench-agent/commit/930c056e29b73f08d7830b496def286012b07697))
* **tau2_agent:** add task_split to EvalConfig model ([f19f5f3](https://github.com/wuTims/tau2-bench-agent/commit/f19f5f3cffd868f3360744fe9df9e3ed021d94e0))
* **tau2_agent:** integrate LLMObs and metrics into server ([4346d5e](https://github.com/wuTims/tau2-bench-agent/commit/4346d5e32e3e46bd83a26c3bbdf3409932a7c2dd))
* **tracing:** add LLMObs span wrapping for A2A agent ([ce15f29](https://github.com/wuTims/tau2-bench-agent/commit/ce15f29bbec2049041245f01dd6ebf8aaac129ec))
* **vacation-rental:** add host consideration and issue handling ([faaec65](https://github.com/wuTims/tau2-bench-agent/commit/faaec65f8605c7af0c5b9fca05a3b3f91ceef0a9))
* **vacation-rental:** add task splits with curated eval subset ([7f00e81](https://github.com/wuTims/tau2-bench-agent/commit/7f00e81e24d2b4c3d85c432d6d52ff28c015e1e8))
* **vacation-rental:** add test data for evidence disputes and edge cases ([b79e6e7](https://github.com/wuTims/tau2-bench-agent/commit/b79e6e7254b36538bbedc6ce0faee2a283d6595f))
* **vacation-rental:** add vacation rental domain ([2efa1b7](https://github.com/wuTims/tau2-bench-agent/commit/2efa1b7a9d7ab958458a00d51bdf29dc03782274))
* **vacation-rental:** standardize task format and add nuanced test scenarios ([53f2135](https://github.com/wuTims/tau2-bench-agent/commit/53f2135bab2510eeaa8dcecec772eab46dde41bf))


### Bug Fixes

* **a2a:** add connect_timeout validation to A2AConfig ([5011982](https://github.com/wuTims/tau2-bench-agent/commit/5011982fabe534b539750bb3b84974f0b1b91ab5))
* **a2a:** add file locking to prevent race in retention cleanup ([6214d55](https://github.com/wuTims/tau2-bench-agent/commit/6214d5507745def592f743bcd614d5e415bdaa48))
* **a2a:** correct SSE event parsing to handle multi-line events ([a8d7c71](https://github.com/wuTims/tau2-bench-agent/commit/a8d7c712c73180f9fcb0586fbe17f8b7a99ccd11))
* **a2a:** handle empty tool_calls and reduce log verbosity ([69fd638](https://github.com/wuTims/tau2-bench-agent/commit/69fd6380b29cfd58683eeb1272b567f6ac0ed6f4))
* **a2a:** handle sessions without progress in retention cleanup ([61d8303](https://github.com/wuTims/tau2-bench-agent/commit/61d83033375f9f1522d280a22dcfee4615cd356b))
* **a2a:** improve JSON-RPC error handling assertions in tests ([1011e1e](https://github.com/wuTims/tau2-bench-agent/commit/1011e1e12ceb585cbe4f980b057480851e055c35))
* **a2a:** improve LiteLLM error handling and add Nebius support ([9e9e243](https://github.com/wuTims/tau2-bench-agent/commit/9e9e243bdab2904707c2f63d956f99fbe9bcd778))
* **a2a:** migrate container registry to Artifact Registry ([62f353c](https://github.com/wuTims/tau2-bench-agent/commit/62f353c3cd4458d0130ab54811bca0d75f05da21))
* **a2a:** remove ineffective file locking from retention cleanup ([d653fd8](https://github.com/wuTims/tau2-bench-agent/commit/d653fd886aba718b76790d7c73298642579bd788))
* **a2a:** require progress for working state events ([6edcd95](https://github.com/wuTims/tau2-bench-agent/commit/6edcd959d5a6bccd0adc981b924f2306447070c0))
* **a2a:** return error dicts instead of raising exceptions ([bb52a29](https://github.com/wuTims/tau2-bench-agent/commit/bb52a29a40c302b4ad29859cc84e940aa19b2982))
* **a2a:** separate full simulation data from trace-compact data ([434fa9b](https://github.com/wuTims/tau2-bench-agent/commit/434fa9bd3c12c07c1916762d022665ff4ae1a24e))
* **a2a:** simplify async handling to prevent concurrency deadlock ([d20b3f5](https://github.com/wuTims/tau2-bench-agent/commit/d20b3f5f1f18dc67280cece1eaa6fdbd175e2add))
* add missing gymnasium dependency ([#91](https://github.com/wuTims/tau2-bench-agent/issues/91)) ([a969a0c](https://github.com/wuTims/tau2-bench-agent/commit/a969a0c0a29bc47ba8580107932f5298ee636045))
* add path traversal protection to get_evaluation_results ([e6f206d](https://github.com/wuTims/tau2-bench-agent/commit/e6f206da3f79cd5cbf866aae80029f002f7db16a))
* add type annotations and input validation ([7bb08cd](https://github.com/wuTims/tau2-bench-agent/commit/7bb08cd5e4c3bbb5ba7399e248b87531dd8e0f45))
* add type safety to phone normalization ([3389c73](https://github.com/wuTims/tau2-bench-agent/commit/3389c739ab1d2bd175652c3489a19fcd26807d2a))
* address CodeRabbit review feedback ([627bb46](https://github.com/wuTims/tau2-bench-agent/commit/627bb4630fad5cd5eb60096e200e150fadd6f6be))
* align tool parameter names with ADK interface ([6c6c15d](https://github.com/wuTims/tau2-bench-agent/commit/6c6c15db547630094fb7804508152d131cdb6e9e))
* apply CodeRabbit review fixes ([211302e](https://github.com/wuTims/tau2-bench-agent/commit/211302ef0c5b2b7576f9a0c263a9ed63461724f6))
* **ci:** lowercase repository owner for Docker tags ([daf44a1](https://github.com/wuTims/tau2-bench-agent/commit/daf44a1bca48dba974ad54e82d76e9ecb50cb47c))
* communicate_info fixed to nl_assertions in Mock domain tasks ([#66](https://github.com/wuTims/tau2-bench-agent/issues/66)) ([702ee77](https://github.com/wuTims/tau2-bench-agent/commit/702ee77e497d89e9d8942ab7206c1a465b12e503))
* **config:** restore litellm/ prefix for model routing ([bf2129d](https://github.com/wuTims/tau2-bench-agent/commit/bf2129d8755620fa7e9b811b8a233241b71ff5b1))
* **data_model:** use dynamic class name in error message ([ffb3909](https://github.com/wuTims/tau2-bench-agent/commit/ffb39099d60218340bbc2f6b6f0cddc837f901eb))
* **datadog:** update demo script for DR-006 monitor ([e0c076a](https://github.com/wuTims/tau2-bench-agent/commit/e0c076aa6c3803e5b8c614d899f538a2af7b95df))
* **datadog:** update Gemini model name in docstring ([0f8c82e](https://github.com/wuTims/tau2-bench-agent/commit/0f8c82ec86fc30c8f2ff6f58d5a471fee186a6f6))
* **deps:** unpin pydantic version constraint ([ca91c84](https://github.com/wuTims/tau2-bench-agent/commit/ca91c84c5ebbea25f0787fd749b2cb82be35b862))
* handle event loop in A2A agent close() method ([f97ce32](https://github.com/wuTims/tau2-bench-agent/commit/f97ce32fa0b81a8d7686919ff2db19a9cd815bab))
* improve datadog e2e test fixtures ([883f15c](https://github.com/wuTims/tau2-bench-agent/commit/883f15c981e1b6f0a2a43ee56b6d4278d1ab71c9))
* improve datadog experiment script robustness ([4a47d3a](https://github.com/wuTims/tau2-bench-agent/commit/4a47d3ab231594ef1e5962776849548a903b4dad))
* improve datadog experiment SSE parsing and test config ([4211492](https://github.com/wuTims/tau2-bench-agent/commit/42114928a90c1de0b50c9d87937875c055bbb07a))
* **kimi-agent:** add missing aiofiles dependency ([e16ba4b](https://github.com/wuTims/tau2-bench-agent/commit/e16ba4b279e2110627841efd53623ad7ee5e3a80))
* normalize phone numbers in telecom domain lookups ([f2397bb](https://github.com/wuTims/tau2-bench-agent/commit/f2397bb952dc3977d367c287ed1b3b9d7c114dda))
* pin pydantic and fix llmobs context manager ([a2c47dd](https://github.com/wuTims/tau2-bench-agent/commit/a2c47ddd822abba78f81438aeb09a9c2b907269c))
* Remove missing submissions from manifest and add images to public directory ([#55](https://github.com/wuTims/tau2-bench-agent/issues/55)) ([462578b](https://github.com/wuTims/tau2-bench-agent/commit/462578b06dcc143c6ad67f75ebe08662dcb98caf))
* restructure port-check control flow and fix lint errors ([e69b233](https://github.com/wuTims/tau2-bench-agent/commit/e69b233185f2102ca82ce7d4cc589e656a248b0b))
* **shared_utils:** add error handling for agent card operations ([d701a1f](https://github.com/wuTims/tau2-bench-agent/commit/d701a1f4ecd2bc0aee00f70ec75ee1f170b219d7))
* target suppress pydantic serialization warnings ([8cbf15f](https://github.com/wuTims/tau2-bench-agent/commit/8cbf15fe72c5527144f4c809eef0b715fb823abb))
* **tau2_agent:** add executor cleanup and API key debug logging ([ca6cd04](https://github.com/wuTims/tau2-bench-agent/commit/ca6cd046706e02a8c7c40dce222a9a6fc275212b))
* **tau2_agent:** add strict config validation to catch typos ([35a16c2](https://github.com/wuTims/tau2-bench-agent/commit/35a16c28333ecda2ebf2709d38f6aa215fdeb9ce))
* **tau2_agent:** disable DD tracing by default for GHCR ([5be023b](https://github.com/wuTims/tau2-bench-agent/commit/5be023b5cc0c7555867923d6988f7df7fc509cfd))
* **tau2_agent:** handle None values in green executor summary formatting ([c9518d8](https://github.com/wuTims/tau2-bench-agent/commit/c9518d8b468d3751b6b3a2d044abdafd9b27a485))
* **tau2_agent:** parse JSON string tool arguments ([f65fe64](https://github.com/wuTims/tau2-bench-agent/commit/f65fe6495ae08986ac3e726fe967c514d96e8f31))
* **tau2_agent:** suppress verbose LLM troubleshooting on errors ([e38e9fb](https://github.com/wuTims/tau2-bench-agent/commit/e38e9fba939fe3f45932c410fb8c5dc01061bf35))
* **tests:** add pytest-xdist and fix Nebius model prefix ([b3bcb46](https://github.com/wuTims/tau2-bench-agent/commit/b3bcb462cbb20361c9b7f39695a5da55f90c19e0))
* **tests:** use specific ValidationError in green executor test ([7277153](https://github.com/wuTims/tau2-bench-agent/commit/72771537bc158af66014752c262536714a311655))
* update datadog experiment to use SSE parser utility ([1b35f56](https://github.com/wuTims/tau2-bench-agent/commit/1b35f56d1ebb5507a6882f4540aa758fe95e8804))
* use keyword-only callback_context parameter ([ca8ef7c](https://github.com/wuTims/tau2-bench-agent/commit/ca8ef7ca3a25f6a8f5b7e00343b25065c1109f5c))
* **vacation-rental:** add default cap for goodwill refund without host profile ([5cc37e0](https://github.com/wuTims/tau2-bench-agent/commit/5cc37e012dffd88a4192c1a2ff05a07b9292cf48))
* **vacation-rental:** correct argument name in Task 28 ([ed3cbe1](https://github.com/wuTims/tau2-bench-agent/commit/ed3cbe170306fef292090cdf6036d7271b8d56be))
* **vacation-rental:** replace eval() with safe AST-based expression parser ([a053aca](https://github.com/wuTims/tau2-bench-agent/commit/a053aca79109019e09d253e33c221a583a60e151))
* verify llm tool response is dict ([f110384](https://github.com/wuTims/tau2-bench-agent/commit/f110384fe8385300b414a628276467f32e3908b4))


### Documentation

* add 007-datadog-project specification ([0abff1e](https://github.com/wuTims/tau2-bench-agent/commit/0abff1e802d87d57463298181b8e3c6b49e7ded2))
* add 008-gcp-integration spec and documentation ([f1c07cc](https://github.com/wuTims/tau2-bench-agent/commit/f1c07cc404d0d4d24a2f9cbcb309f57788011ba7))
* add A2A integration guide and developer tooling ([8a1995c](https://github.com/wuTims/tau2-bench-agent/commit/8a1995c42af8f146d473afc104c3c772826c8a5a))
* add async evaluation specification ([ae72a50](https://github.com/wuTims/tau2-bench-agent/commit/ae72a509c363f9a66ba7fc5ef696bb5c6c19f60e))
* add datadog enhancements specification ([f25f3d5](https://github.com/wuTims/tau2-bench-agent/commit/f25f3d5d288b1070ebda2ea769e5a9eb4a377f31))
* add documentation skill and expand testing skill ([3151024](https://github.com/wuTims/tau2-bench-agent/commit/3151024d84c3c2faab3423016f595decb646d6f1))
* add evaluation store specification ([2d4c92e](https://github.com/wuTims/tau2-bench-agent/commit/2d4c92e1d0b12cc4bb68a01f56fc9afb957cd4c0))
* add local testing guides and developer scripts ([08232ed](https://github.com/wuTims/tau2-bench-agent/commit/08232eda6a674f5474b9eade486071a4fa246617))
* **agentbeats:** add initial agentbeats integration plan ([998abfd](https://github.com/wuTims/tau2-bench-agent/commit/998abfda0c9a231f0b91f8ce3183d18952cbc909))
* **agentbeats:** update example model to Qwen3-235B ([881fa38](https://github.com/wuTims/tau2-bench-agent/commit/881fa381e64c60a032f1d3fce538bd73a58aa727))
* **commit:** add push and PR creation phases ([9adbf8b](https://github.com/wuTims/tau2-bench-agent/commit/9adbf8b99f743e9f0cceb27a32c4f7258dc801c3))
* consolidate sequence diagrams in quickstart ([1d9529f](https://github.com/wuTims/tau2-bench-agent/commit/1d9529f917e15734ca7b0e77aa7bd24331a1ed7e))
* fix CLAUDE.md command formatting ([e95eda1](https://github.com/wuTims/tau2-bench-agent/commit/e95eda16a496ddcb98e56219e9748e5f932c52aa))
* fix type hints in async evaluation spec ([0651d04](https://github.com/wuTims/tau2-bench-agent/commit/0651d04a9848b61592004f1fd69d3eee247fb70b))
* improve A2A integration documentation ([35977d0](https://github.com/wuTims/tau2-bench-agent/commit/35977d03608bf58823781209db15e85cd5b833e2))
* **readme:** add Docker deployment option ([a0fd737](https://github.com/wuTims/tau2-bench-agent/commit/a0fd7371ef8206ae95d3a975ba90d13c5c9f7501))
* update A2A agent port numbers ([787399a](https://github.com/wuTims/tau2-bench-agent/commit/787399ad33b6649273288757d5d11c9a4ea00cad))
* update CLAUDE.md for 008-gcp-integration ([ef60ce8](https://github.com/wuTims/tau2-bench-agent/commit/ef60ce81d0a72fbbe9d809e491525a69e0d82b45))
* update CLAUDE.md with project guidelines ([00f5863](https://github.com/wuTims/tau2-bench-agent/commit/00f5863a046b20c80ded6ee74ad729c633b33c9e))
* update documentation for quickstart and diagrams ([5dd7e22](https://github.com/wuTims/tau2-bench-agent/commit/5dd7e22d45a5ac55ce1c8f7d1b40e58f81312eee))
* update skill documentation and spec ([8786ac1](https://github.com/wuTims/tau2-bench-agent/commit/8786ac193a7cc511f7ec16f757a4757a4385d8ac))
* update tasks.md with Phase 1-2 completion status and implementation notes ([d354840](https://github.com/wuTims/tau2-bench-agent/commit/d354840e81076aab069cead0e071eb56dc6f9223))
* **vacation-rental:** add domain README with three-layer decision model design ([cf56c21](https://github.com/wuTims/tau2-bench-agent/commit/cf56c21e2ae893fa834086eb83ccbfc09514bdbb))
* **vacation-rental:** fix get_guest_history function signature ([8beff17](https://github.com/wuTims/tau2-bench-agent/commit/8beff179fe2199743f20cf1a00d227cbc3b57d0e))

## [Unreleased]

### Added

### Changed

### Deprecated

### Removed

### Fixed

### Security

## [0.2.1] - 2025-11-07
### Added
- Gymnasium-compatible interface for RL training with `AgentGymEnv` and `UserGymEnv`
- Train/test task splits for all domains
- Interactive play mode (`tau2 play`) supporting both agent and user roles
- Possibility to strictly enforce communication protocol rules (e.g., no mixed messages with text and tool calls)

## [0.2.0] - 2025-10-06

### Added
- Web-based leaderboard system with interactive submission management
- GitHub Pages deployment for leaderboard with automated CI/CD
- Comprehensive submission validation and verification system
- Model comparison interface with performance metrics visualization
- Trajectory visualization in web interface
- Mobile-responsive leaderboard design
- Logo assets and branding for multiple LLM providers
- Live leaderboard deployment at tau-bench.com

### Changed
- Enhanced submission manifest structure
- Improved image handling and asset management
- Updated deployment workflow for better reliability

### Fixed
- Mobile view responsiveness issues
- Missing submissions from manifest
- Image path resolution for GitHub Pages deployment
- Base URL handling for subdirectory deployment

## [0.1.3] - 2025-08-26

### Fixed
- LLM arguments parsing and handling
- Removed default natural language assertion checks that were causing issues

## [0.1.2] - 2025-07-17

### Added
- `tau2 check-data` CLI command for verifying data directory setup
- Support for `TAU2_DATA_DIR` environment variable for non-editable installs
- Fallback to local source when data directory is not set
- `--num-tasks` CLI flag for limiting task count

### Changed
- Made `pip install -e .` the default installation method
- Improved task name display in CLI
- Enhanced data directory configuration flexibility

### Fixed
- Installation issues with data directory discovery
- Task filtering and display problems

## [0.1.1] - 2025-06-12

### Fixed
- Domain viewer CLI functionality
- `tau2 domain` command execution issues

## [0.1.0] - 2025-06-12

### Added
- Initial release of τ²-bench framework
- Support for multiple domains: mock, airline, retail, telecom
- Command-line interface with `tau2` command
- Agent evaluation system with LLM integration via LiteLLM
- User simulator for realistic conversation scenarios
- Environment system with domain-specific tools and policies
- Orchestration system for managing agent-user-environment interactions
- Comprehensive test suite
- Domain-specific documentation and API endpoints
- Experimental features: no-user mode, oracle-plan mode, workflow policies
- Support for ablation studies
- Interactive environment CLI for testing and debugging
- Caching system for LLM calls (Redis-based)
- Multi-trial evaluation with concurrent execution support

### Technical Details
- Python 3.10+ support
- FastAPI-based web services
- Pydantic data models
- Rich CLI with tabulated output
- Comprehensive logging with Loguru
- Performance metrics and visualization
- Configurable LLM backends
- Semantic versioning adoption

## Links
- [Repository](https://github.com/sierra-research/tau2-bench)
- [Leaderboard](https://tau-bench.com)
- [Paper](https://arxiv.org/abs/2506.07982)
- [Blog Post](https://sierra.ai/blog/benchmarking-agents-in-collaborative-real-world-scenarios)
