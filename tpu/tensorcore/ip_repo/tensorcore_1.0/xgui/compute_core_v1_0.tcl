# Definitional proc to organize widgets for parameters.
proc init_gui { IPINST } {
  ipgui::add_param $IPINST -name "Component_Name"
  #Adding Page
  set Page_0 [ipgui::add_page $IPINST -name "Page 0"]
  ipgui::add_param $IPINST -name "ADDR_WIDTH" -parent ${Page_0}
  ipgui::add_param $IPINST -name "DATA_WIDTH" -parent ${Page_0}
  ipgui::add_param $IPINST -name "NUM_BANKS" -parent ${Page_0}
  ipgui::add_param $IPINST -name "VPU_ADDR_W" -parent ${Page_0}
  ipgui::add_param $IPINST -name "VPU_DATA_W" -parent ${Page_0}
  ipgui::add_param $IPINST -name "VPU_IADDR_W" -parent ${Page_0}
  ipgui::add_param $IPINST -name "VPU_OP_W" -parent ${Page_0}


}

proc update_PARAM_VALUE.ADDR_WIDTH { PARAM_VALUE.ADDR_WIDTH } {
	# Procedure called to update ADDR_WIDTH when any of the dependent parameters in the arguments change
}

proc validate_PARAM_VALUE.ADDR_WIDTH { PARAM_VALUE.ADDR_WIDTH } {
	# Procedure called to validate ADDR_WIDTH
	return true
}

proc update_PARAM_VALUE.DATA_WIDTH { PARAM_VALUE.DATA_WIDTH } {
	# Procedure called to update DATA_WIDTH when any of the dependent parameters in the arguments change
}

proc validate_PARAM_VALUE.DATA_WIDTH { PARAM_VALUE.DATA_WIDTH } {
	# Procedure called to validate DATA_WIDTH
	return true
}

proc update_PARAM_VALUE.NUM_BANKS { PARAM_VALUE.NUM_BANKS } {
	# Procedure called to update NUM_BANKS when any of the dependent parameters in the arguments change
}

proc validate_PARAM_VALUE.NUM_BANKS { PARAM_VALUE.NUM_BANKS } {
	# Procedure called to validate NUM_BANKS
	return true
}

proc update_PARAM_VALUE.VPU_ADDR_W { PARAM_VALUE.VPU_ADDR_W } {
	# Procedure called to update VPU_ADDR_W when any of the dependent parameters in the arguments change
}

proc validate_PARAM_VALUE.VPU_ADDR_W { PARAM_VALUE.VPU_ADDR_W } {
	# Procedure called to validate VPU_ADDR_W
	return true
}

proc update_PARAM_VALUE.VPU_DATA_W { PARAM_VALUE.VPU_DATA_W } {
	# Procedure called to update VPU_DATA_W when any of the dependent parameters in the arguments change
}

proc validate_PARAM_VALUE.VPU_DATA_W { PARAM_VALUE.VPU_DATA_W } {
	# Procedure called to validate VPU_DATA_W
	return true
}

proc update_PARAM_VALUE.VPU_IADDR_W { PARAM_VALUE.VPU_IADDR_W } {
	# Procedure called to update VPU_IADDR_W when any of the dependent parameters in the arguments change
}

proc validate_PARAM_VALUE.VPU_IADDR_W { PARAM_VALUE.VPU_IADDR_W } {
	# Procedure called to validate VPU_IADDR_W
	return true
}

proc update_PARAM_VALUE.VPU_OP_W { PARAM_VALUE.VPU_OP_W } {
	# Procedure called to update VPU_OP_W when any of the dependent parameters in the arguments change
}

proc validate_PARAM_VALUE.VPU_OP_W { PARAM_VALUE.VPU_OP_W } {
	# Procedure called to validate VPU_OP_W
	return true
}


proc update_MODELPARAM_VALUE.ADDR_WIDTH { MODELPARAM_VALUE.ADDR_WIDTH PARAM_VALUE.ADDR_WIDTH } {
	# Procedure called to set VHDL generic/Verilog parameter value(s) based on TCL parameter value
	set_property value [get_property value ${PARAM_VALUE.ADDR_WIDTH}] ${MODELPARAM_VALUE.ADDR_WIDTH}
}

proc update_MODELPARAM_VALUE.DATA_WIDTH { MODELPARAM_VALUE.DATA_WIDTH PARAM_VALUE.DATA_WIDTH } {
	# Procedure called to set VHDL generic/Verilog parameter value(s) based on TCL parameter value
	set_property value [get_property value ${PARAM_VALUE.DATA_WIDTH}] ${MODELPARAM_VALUE.DATA_WIDTH}
}

proc update_MODELPARAM_VALUE.NUM_BANKS { MODELPARAM_VALUE.NUM_BANKS PARAM_VALUE.NUM_BANKS } {
	# Procedure called to set VHDL generic/Verilog parameter value(s) based on TCL parameter value
	set_property value [get_property value ${PARAM_VALUE.NUM_BANKS}] ${MODELPARAM_VALUE.NUM_BANKS}
}

proc update_MODELPARAM_VALUE.VPU_DATA_W { MODELPARAM_VALUE.VPU_DATA_W PARAM_VALUE.VPU_DATA_W } {
	# Procedure called to set VHDL generic/Verilog parameter value(s) based on TCL parameter value
	set_property value [get_property value ${PARAM_VALUE.VPU_DATA_W}] ${MODELPARAM_VALUE.VPU_DATA_W}
}

proc update_MODELPARAM_VALUE.VPU_ADDR_W { MODELPARAM_VALUE.VPU_ADDR_W PARAM_VALUE.VPU_ADDR_W } {
	# Procedure called to set VHDL generic/Verilog parameter value(s) based on TCL parameter value
	set_property value [get_property value ${PARAM_VALUE.VPU_ADDR_W}] ${MODELPARAM_VALUE.VPU_ADDR_W}
}

proc update_MODELPARAM_VALUE.VPU_OP_W { MODELPARAM_VALUE.VPU_OP_W PARAM_VALUE.VPU_OP_W } {
	# Procedure called to set VHDL generic/Verilog parameter value(s) based on TCL parameter value
	set_property value [get_property value ${PARAM_VALUE.VPU_OP_W}] ${MODELPARAM_VALUE.VPU_OP_W}
}

proc update_MODELPARAM_VALUE.VPU_IADDR_W { MODELPARAM_VALUE.VPU_IADDR_W PARAM_VALUE.VPU_IADDR_W } {
	# Procedure called to set VHDL generic/Verilog parameter value(s) based on TCL parameter value
	set_property value [get_property value ${PARAM_VALUE.VPU_IADDR_W}] ${MODELPARAM_VALUE.VPU_IADDR_W}
}

