# Moodle Web Service Konfigurazioa - Feedback Client

## Informazio Orokorra

| Datu | Balioa |
|------|--------|
| **Moodle URL** | http://192.168.1.227 |
| **Zerbitzuaren izena** | Moodle Feedback Client Service |
| **Short name** | moodle_feedback_client |
| **Zerbitzuaren ID** | 9 |
| **Erabiltzailea** | BIRT LH (laguntza@birt.eus) |
| **Token izena** | Moodle_Feedback_Service_Token |
| **Token balioa** | `26b373ba0d09b64de3b5de276381a520` |
| **Iraungitze data** | Ez du iraungitze datarik |

---

## 1. Pausua: Web Zerbitzuak Aktibatu

1. Sartu Moodle administrazio panelean
2. Joan **Administración del sitio** → **Servidor** → **Servicios web**
3. Ziurtatu **Habilitar servicios web** aktibatuta dagoela

---

## 2. Pausua: REST Protokoloa Aktibatu

1. Joan **Administración del sitio** → **Servidor** → **Servicios web** → **Administrar protocolos**
2. Aktibatu **REST protokoloa** (begiak irekita)

---

## 3. Pausua: Zerbitzu Berria Sortu

1. Joan **Administración del sitio** → **Servidor** → **Servicios web** → **Servicios externos**
2. Klikatu **Agregar** zerbitzu berri bat sortzeko
3. Sartu datu hauek:
   - **Nombre**: `Moodle Feedback Client Service`
   - **Nombre corto**: `moodle_feedback_client`
   - **Habilitado**: ✅ Bai
   - **Únicamente usuarios autorizados**: ✅ Bai
4. Gorde aldaketak

---

## 4. Pausua: API Funtzioak Gehitu

Zerbitzuari 9 funtzio gehitu zitzaizkion:

| # | Funtzio Izena | Deskribapena |
|---|---------------|--------------|
| 1 | `core_course_get_contents` | Kurtsoko edukiak lortu |
| 2 | `core_course_search_courses` | Kurtsoak bilatu |
| 3 | `core_enrol_get_enrolled_users` | Matrikulatutako erabiltzaileak lortu |
| 4 | `mod_assign_get_assignments` | Zereginak lortu |
| 5 | `mod_assign_get_submissions` | Bidalketa/entregak lortu |
| 6 | `mod_quiz_get_quizzes_by_courses` | Kurtsoko galdetegiak lortu |
| 7 | `mod_quiz_get_user_attempts` | Erabiltzailearen saiakerak lortu |
| 8 | `mod_quiz_get_user_best_grade` | Erabiltzailearen nota onena lortu |
| 9 | `mod_vpl_open` | VPL zereginak ireki |

### Funtzioak gehitzeko pausuak:

1. Joan zerbitzuaren konfiguraziora: `service_functions.php?id=9`
2. Klikatu **Agregar funciones**
3. Bilatu eta hautatu funtzio bakoitza
4. Gorde aldaketak

---

## 5. Pausua: Erabiltzailea Baimendu

> ⚠️ **Oharra**: Zerbitzua "Únicamente usuarios autorizados" moduan dagoenez, erabiltzailea eskuz baimendu behar da.

1. Joan zerbitzuaren editatzera
2. Klikatu **Usuarios autorizados** atalean
3. Gehitu **BIRT LH** erabiltzailea baimendutako zerrendara
4. Gorde aldaketak

---

## 6. Pausua: Token Sortu

1. Joan **Administración del sitio** → **Servidor** → **Servicios web** → **Administrar tokens**
2. Klikatu **Crear token**
3. Bete formularioa:
   - **Nombre**: `Moodle_Feedback_Service_Token`
   - **Servicio**: `Moodle Feedback Client Service`
   - **Usuario**: `BIRT LH`
   - **Habilitar fecha de expiración**: ❌ Desaktibatu (iraungitze datarik gabe)
   - **Restricción IP**: Hutsik utzi
4. Klikatu **Guardar cambios**
5. **GARRANTZITSUA**: Kopiatu tokena berehala! Orritik irtetean ez da berriro erakutsiko.

---

## Token Erabilera

### API Deia Egiteko Adibidea

```bash
curl "http://192.168.1.227/webservice/rest/server.php?wstoken=26b373ba0d09b64de3b5de276381a520&wsfunction=core_course_search_courses&moodlewsrestformat=json&criterianame=search&criteriavalue=test"
```

### Python Adibidea

```python
import requests

MOODLE_URL = "http://192.168.1.227"
TOKEN = "26b373ba0d09b64de3b5de276381a520"

def call_moodle_api(function_name, **params):
    url = f"{MOODLE_URL}/webservice/rest/server.php"
    params.update({
        'wstoken': TOKEN,
        'wsfunction': function_name,
        'moodlewsrestformat': 'json'
    })
    response = requests.get(url, params=params)
    return response.json()

# Adibidea: Kurtsoak bilatu
result = call_moodle_api('core_course_search_courses', 
                         criterianame='search', 
                         criteriavalue='programazioa')
print(result)
```

---

## Ingurune Aldagaiak

Proiektuan `.env` fitxategi bat sortzea gomendatzen da:

```env
MOODLE_URL=http://192.168.1.227
MOODLE_TOKEN=26b373ba0d09b64de3b5de276381a520
```

---

## Arazoak eta Konponbideak

### Errorea: "El usuario no tiene permitido este servicio"

**Kausa**: Erabiltzailea ez dago baimendutako zerrendan.

**Konponbidea**: 
1. Joan zerbitzuaren konfiguraziora
2. Gehitu erabiltzailea "Usuarios autorizados" atalean

### Errorea: "Invalid token"

**Kausa posibleak**:
- Token okerra
- Tokena iraungita
- Zerbitzua desaktibatuta

**Konponbidea**: Egiaztatu token balioa eta zerbitzuaren egoera.

---

## Dokumentua Sortu

- **Data**: 2025-11-27
- **Egilea**: Mikel Aldalur
- **Proiektua**: Moodle Feedback Client
