-- Схема конфигурации для Kong плагина
local typedefs = require "kong.db.schema.typedefs"

return {
  name = "widget-domain-check",
  fields = {
    {
      -- Конфигурация плагина
      config = {
        type = "record",
        fields = {
          {
            db_host = {
              type = "string",
              required = true,
              default = "operator-db"
            }
          },
          {
            db_port = {
              type = "integer",
              required = true,
              default = 5432
            }
          },
          {
            db_name = {
              type = "string",
              required = true,
              default = "operator_db"
            }
          },
          {
            db_user = {
              type = "string",
              required = true,
              default = "operator_service"
            }
          },
          {
            db_password = {
              type = "string",
              required = true,
              default = "operator_password",
              encrypted = true  -- Шифрование пароля
            }
          },
        }
      }
    }
  }
}
