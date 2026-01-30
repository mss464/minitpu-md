# Mini-TPU ASIC Build Makefile
# Target: IHP SG13G2 via OpenROAD-flow-scripts Docker

DOCKER_IMAGE := openroad/orfs:latest
PROJECT_ROOT := $(shell pwd)/..
DESIGN       := tpu_core
PLATFORM     := ihp-sg13g2

# Docker mount options
DOCKER_OPTS := -v $(PROJECT_ROOT):/design -w /OpenROAD-flow-scripts/flow

.PHONY: all setup synth place route finish clean gui help shell

help:
	@echo "Mini-TPU ASIC Build System (Docker-based)"
	@echo ""
	@echo "Targets:"
	@echo "  setup    - Copy design files into Docker container workspace"
	@echo "  synth    - Run synthesis (Yosys)"
	@echo "  place    - Run floorplan + placement"
	@echo "  route    - Run CTS + routing"
	@echo "  finish   - Complete flow to GDS"
	@echo "  gui      - Open OpenROAD GUI (requires X11)"
	@echo "  shell    - Open interactive shell in Docker"
	@echo "  clean    - Clean build artifacts"
	@echo ""

all: finish

# Copy RTL and config to ORFS structure inside container
setup:
	docker run --rm $(DOCKER_OPTS) $(DOCKER_IMAGE) bash -c "\
		mkdir -p designs/src/$(DESIGN) && \
		mkdir -p designs/$(PLATFORM)/$(DESIGN) && \
		cp /design/tpu/*.sv designs/src/$(DESIGN)/ || true && \
		cp /design/asic/src/*.sv designs/src/$(DESIGN)/ && \
		cp /design/asic/$(PLATFORM)/config.mk designs/$(PLATFORM)/$(DESIGN)/ && \
		cp /design/asic/$(PLATFORM)/constraint.sdc designs/$(PLATFORM)/$(DESIGN)/ && \
		echo 'Setup complete'"

synth:
	docker run --rm $(DOCKER_OPTS) $(DOCKER_IMAGE) bash -c "\
		source ../env.sh && \
		make synth DESIGN_CONFIG=designs/$(PLATFORM)/$(DESIGN)/config.mk"

place:
	docker run --rm $(DOCKER_OPTS) $(DOCKER_IMAGE) bash -c "\
		source ../env.sh && \
		make place DESIGN_CONFIG=designs/$(PLATFORM)/$(DESIGN)/config.mk"

route:
	docker run --rm $(DOCKER_OPTS) $(DOCKER_IMAGE) bash -c "\
		source ../env.sh && \
		make route DESIGN_CONFIG=designs/$(PLATFORM)/$(DESIGN)/config.mk"

finish:
	docker run --rm $(DOCKER_OPTS) $(DOCKER_IMAGE) bash -c "\
		source ../env.sh && \
		make finish DESIGN_CONFIG=designs/$(PLATFORM)/$(DESIGN)/config.mk"
	@echo ""
	@echo "GDS output: results/$(PLATFORM)/$(DESIGN)/base/6_final.gds"

shell:
	docker run -it $(DOCKER_OPTS) $(DOCKER_IMAGE) bash

clean:
	docker run --rm $(DOCKER_OPTS) $(DOCKER_IMAGE) bash -c "\
		make clean_all DESIGN_CONFIG=designs/$(PLATFORM)/$(DESIGN)/config.mk 2>/dev/null || true"
