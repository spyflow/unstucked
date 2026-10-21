import os
import sys
import platform
import subprocess
import tempfile
from getpass import getpass
from xml.sax.saxutils import escape


def add_eduroam_linux(username: str, password: str):
    # Detectar interfaz Wi-Fi activa o usar comodín
    res = subprocess.run(
        ["nmcli", "-t", "-f", "DEVICE,TYPE", "device"],
        capture_output=True, text=True, check=True
    )
    wifi_iface = "*"
    for line in res.stdout.splitlines():
        if line.endswith(":wifi"):
            wifi_iface = line.split(":")[0]
            break

    # Eliminar perfil previo si existe
    subprocess.run(
        ["nmcli", "connection", "delete", "eduroam"],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
    )

    # Crear perfil ignorando certificado y permitiendo TLS heredado (phase1-auth-flags 32)
    cmd = [
        "nmcli", "connection", "add",
        "type", "wifi",
        "con-name", "eduroam",
        "ifname", wifi_iface,
        "ssid", "eduroam",
        "wifi-sec.key-mgmt", "wpa-eap",
        "802-1x.eap", "peap",
        "802-1x.phase2-auth", "mschapv2",
        "802-1x.identity", username,
        "802-1x.password", password,
        "802-1x.password-flags", "0",
        "802-1x.system-ca-certs", "no",
        "802-1x.phase1-auth-flags", "32"
    ]
    subprocess.run(cmd, check=True)
    
    # Intentar levantar la conexión automáticamente
    subprocess.run(["nmcli", "connection", "up", "eduroam"])
    print("Perfil 'eduroam' agregado y conectado correctamente en Linux.")


def add_eduroam_windows(username: str, password: str):
    import ctypes
    from ctypes import wintypes

    profile_xml = """<?xml version="1.0"?>
<WLANProfile xmlns="http://www.microsoft.com/networking/WLAN/profile/v1">
    <name>eduroam</name>
    <SSIDConfig>
        <SSID>
            <name>eduroam</name>
        </SSID>
    </SSIDConfig>
    <connectionType>ESS</connectionType>
    <connectionMode>auto</connectionMode>
    <MSM>
        <security>
            <authEncryption>
                <authentication>WPA2</authentication>
                <encryption>AES</encryption>
                <useOneX>true</useOneX>
            </authEncryption>
            <OneX xmlns="http://www.microsoft.com/networking/OneX/v1">
                <EAPConfig>
                    <EapHostConfig xmlns="http://www.microsoft.com/provisioning/EapHostConfig">
                        <EapMethod>
                            <Type xmlns="http://www.microsoft.com/provisioning/EapCommon">25</Type>
                            <VendorId xmlns="http://www.microsoft.com/provisioning/EapCommon">0</VendorId>
                            <VendorType xmlns="http://www.microsoft.com/provisioning/EapCommon">0</VendorType>
                            <AuthorId xmlns="http://www.microsoft.com/provisioning/EapCommon">0</AuthorId>
                        </EapMethod>
                        <Config xmlns="http://www.microsoft.com/provisioning/EapHostConfig">
                            <Eap xmlns="http://www.microsoft.com/provisioning/BaseEapConnectionPropertiesV1">
                                <Type>25</Type>
                                <EapType xmlns="http://www.microsoft.com/provisioning/MsPeapConnectionPropertiesV1">
                                    <ServerValidation>
                                        <DisableUserPromptForServerValidation>true</DisableUserPromptForServerValidation>
                                        <ServerNames></ServerNames>
                                    </ServerValidation>
                                    <FastReconnect>true</FastReconnect>
                                    <InnerEapOptional>false</InnerEapOptional>
                                    <Eap xmlns="http://www.microsoft.com/provisioning/BaseEapConnectionPropertiesV1">
                                        <Type>26</Type>
                                        <EapType xmlns="http://www.microsoft.com/provisioning/MsChapV2ConnectionPropertiesV1">
                                            <UseWinLogonCredentials>false</UseWinLogonCredentials>
                                        </EapType>
                                    </Eap>
                                    <EnableQuarantineChecks>false</EnableQuarantineChecks>
                                    <RequireCryptoBinding>false</RequireCryptoBinding>
                                    <PeapExtensions>
                                        <PerformServerValidation xmlns="http://www.microsoft.com/provisioning/MsPeapConnectionPropertiesV2">false</PerformServerValidation>
                                        <AcceptServerName xmlns="http://www.microsoft.com/provisioning/MsPeapConnectionPropertiesV2">false</AcceptServerName>
                                    </PeapExtensions>
                                </EapType>
                            </Eap>
                        </Config>
                    </EapHostConfig>
                </EapConfig>
            </OneX>
        </security>
    </MSM>
</WLANProfile>"""

    user_xml = f"""<?xml version="1.0"?>
<EapHostUserCredentials xmlns="http://www.microsoft.com/provisioning/EapHostUserCredentials" xmlns:eapCommon="http://www.microsoft.com/provisioning/EapCommon" xmlns:baseEap="http://www.microsoft.com/provisioning/BaseEapMethodUserCredentials">
    <EapMethod>
        <eapCommon:Type>25</eapCommon:Type>
        <eapCommon:AuthorId>0</eapCommon:AuthorId>
    </EapMethod>
    <Credentials xmlns:eapUser="http://www.microsoft.com/provisioning/EapUserPropertiesV1" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xmlns:baseEap="http://www.microsoft.com/provisioning/BaseEapUserPropertiesV1" xmlns:MsPeap="http://www.microsoft.com/provisioning/MsPeapUserPropertiesV1" xmlns:MsChapV2="http://www.microsoft.com/provisioning/MsChapV2UserPropertiesV1">
        <baseEap:Eap>
            <baseEap:Type>25</baseEap:Type>
            <MsPeap:EapType>
                <MsPeap:RoutingIdentity>{escape(username)}</MsPeap:RoutingIdentity>
                <baseEap:Eap>
                    <baseEap:Type>26</baseEap:Type>
                    <MsChapV2:EapType>
                        <MsChapV2:Username>{escape(username)}</MsChapV2:Username>
                        <MsChapV2:Password>{escape(password)}</MsChapV2:Password>
                        <MsChapV2:Domain></MsChapV2:Domain>
                    </MsChapV2:EapType>
                </baseEap:Eap>
            </MsPeap:EapType>
        </baseEap:Eap>
    </Credentials>
</EapHostUserCredentials>"""

    # 1. Importar perfil de red con netsh
    with tempfile.NamedTemporaryFile("w", suffix=".xml", delete=False, encoding="utf-8") as tmp:
        tmp.write(profile_xml)
        tmp_path = tmp.name

    try:
        subprocess.run(["netsh", "wlan", "add", "profile", f"filename={tmp_path}"], check=True)
    finally:
        os.remove(tmp_path)

    # 2. Guardar credenciales de usuario en el perfil mediante wlanapi.dll
    wlanapi = ctypes.WinDLL("wlanapi.dll")

    class GUID(ctypes.Structure):
        _fields_ = [
            ("Data1", wintypes.DWORD),
            ("Data2", wintypes.WORD),
            ("Data3", wintypes.WORD),
            ("Data4", wintypes.BYTE * 8),
        ]

    class WLAN_INTERFACE_INFO(ctypes.Structure):
        _fields_ = [
            ("InterfaceGuid", GUID),
            ("strInterfaceDescription", wintypes.WCHAR * 256),
            ("isState", ctypes.c_uint),
        ]

    class WLAN_INTERFACE_INFO_LIST(ctypes.Structure):
        _fields_ = [
            ("dwNumberOfItems", wintypes.DWORD),
            ("dwIndex", wintypes.DWORD),
            ("InterfaceInfo", WLAN_INTERFACE_INFO * 1),
        ]

    handle = wintypes.HANDLE()
    negotiated_version = wintypes.DWORD()
    if wlanapi.WlanOpenHandle(2, None, ctypes.byref(negotiated_version), ctypes.byref(handle)) != 0:
        raise RuntimeError("No se pudo abrir el handle de WLAN.")

    iface_list_ptr = ctypes.POINTER(WLAN_INTERFACE_INFO_LIST)()
    if wlanapi.WlanEnumInterfaces(handle, None, ctypes.byref(iface_list_ptr)) != 0:
        wlanapi.WlanCloseHandle(handle, None)
        raise RuntimeError("No se pudieron enumerar las interfaces Wi-Fi.")

    try:
        if iface_list_ptr.contents.dwNumberOfItems == 0:
            raise RuntimeError("No se encontraron adaptadores Wi-Fi.")

        iface_guid = iface_list_ptr.contents.InterfaceInfo[0].InterfaceGuid
        res = wlanapi.WlanSetProfileEapXmlUserData(
            handle,
            ctypes.byref(iface_guid),
            ctypes.c_wchar_p("eduroam"),
            0,
            ctypes.c_wchar_p(user_xml),
            None
        )
        if res != 0:
            raise RuntimeError(f"Error al guardar las credenciales EAP (Código: {res}).")
    finally:
        wlanapi.WlanFreeMemory(iface_list_ptr)
        wlanapi.WlanCloseHandle(handle, None)

    print("Perfil 'eduroam' y credenciales agregados correctamente en Windows.")


def main():
    username = input("Username: ").strip()
    password = getpass("Password: ")

    sistema = platform.system()
    if sistema == "Linux":
        add_eduroam_linux(username, password)
    elif sistema == "Windows":
        add_eduroam_windows(username, password)
    else:
        print(f"Sistema operativo no soportado por el script: {sistema}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
