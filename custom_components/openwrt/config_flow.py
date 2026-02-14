"""Config flow for openwrt integration."""
import voluptuous as vol
from homeassistant import config_entries
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .const import DOMAIN, CONF_HOST, CONF_USERNAME, CONF_PASSWORD, CONF_UPDATE_INTERVAL
from .api import OpenWrtApi, OpenWrtAuthError

class FlowHandler(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle config flow."""
    
    VERSION = 1

    async def async_step_user(self, user_input=None):
        errors = {}
        
        if user_input is not None:
            session = async_get_clientsession(self.hass)

            api = OpenWrtApi(
                user_input[CONF_HOST],
                user_input[CONF_USERNAME],
                user_input[CONF_PASSWORD],
                session
            )

            try:
                if await api.login():
                    await self.async_set_unique_id(f"openwrt-{user_input[CONF_HOST]}")
                    self._abort_if_unique_id_configured()
                    
                    return self.async_create_entry(
                        title=user_input[CONF_HOST], 
                        data=user_input
                    )
                else:
                    errors["base"] = "cannot_connect"
            except OpenWrtAuthError:
                errors["base"] = "invalid_auth"
            except Exception:
                errors["base"] = "unknown"

        schema = vol.Schema({
            vol.Required(CONF_HOST, default="http://192.168.1.1"): str,
            vol.Required(CONF_USERNAME, default="root"): str,
            vol.Required(CONF_PASSWORD): str,
        })

        return self.async_show_form(step_id="user", data_schema=schema, errors=errors)

    @staticmethod
    def async_get_options_flow(config_entry):
        return OptionsFlowHandler(config_entry)

class OptionsFlowHandler(config_entries.OptionsFlow):
    def __init__(self, config_entry):
        super().__init__()

    async def async_step_init(self, user_input=None):
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema({
                vol.Optional(
                    CONF_UPDATE_INTERVAL,
                    default=self.config_entry.options.get(CONF_UPDATE_INTERVAL, 10),
                ): vol.All(vol.Coerce(int), vol.Range(min=5, max=3600))
            }),
        )