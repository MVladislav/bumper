from collections import defaultdict

# Your cleaned domain list goes here
domains = [
    "a1zYhiMF5J3.iot-as-mqtt.cn-shanghai.aliyuncs.com",
    "mpush-api.aliyun.com",
    "sdk.openaccount.aliyun.com",
    "itls.eu-central-1.aliyuncs.com",
    "eu-central-1.aliyuncs.com",
    "ca.robotww.ecouser.net",
    "ca.robotcn.ecouser.net",
    "robotcn.ecouser.net",
    "dc.robotcn.ecouser.net",
    "area.robotww.ecouser.net",
    "area.robotcn.ecouser.net",
    "autodiscover.ecovacs.com",
    "cfjump.ecovacs.com",
    "checkout-au.ecovacs.com",
    "checkout-test.ecovacs.com",
    "checkout-uk.ecovacs.com",
    "comingsoon.ecovacs.com",
    "czjquw.ecovacs.com",
    "ecovacs.com",
    "eml.ecovacs.com",
    "www.eml.ecovacs.com",
    "exchange.ecovacs.com",
    "gl-de-api.ecovacs.com",
    "gl-de-openapi.ecovacs.com",
    "gl-us-pub.ecovacs.com",
    "mail.ecovacs.com",
    "parts-apac.ecovacs.com",
    "qdbdrg.ecovacs.com",
    "recommender.ecovacs.com",
    "sa-eu-datasink.ecovacs.com",
    "site-static.ecovacs.com",
    "store-de.ecovacs.com",
    "store-fr.ecovacs.com",
    "storehk.ecovacs.com",
    "store-it.ecovacs.com",
    "store-jp.ecovacs.com",
    "storesg.ecovacs.com",
    "store-uk.ecovacs.com",
    "usshop.ecovacs.com",
    "vpn.ecovacs.com",
    "dc-cn.bizcn.ecouser.net",
    "dc-as.bizww.ecouser.net",
    "dc-eu.bizww.ecouser.net",
    "dc-na.bizww.ecouser.net",
    "dc-cn.app.cn.ecouser.net",
    "area.cn.ecouser.net",
    "dc-cn.base.cn.ecouser.net",
    "cloud-ui.dc-cn.cloud.cn.ecouser.net",
    "dc-cn.cloud.cn.ecouser.net",
    "cn.ecouser.net",
    "cn.dc.cn.ecouser.net",
    "dc-cn.cn.ecouser.net",
    "dc.cn.ecouser.net",
    "dc-hq.cn.ecouser.net",
    "dc-cn.ngiot.cn.ecouser.net",
    "dc-cn.rapp.cn.ecouser.net",
    "dc-cn.rop.cn.ecouser.net",
    "dc.ecouser.net",
    "dev.ecouser.net",
    "dc-hq.devhq.ecouser.net",
    "dl.ecouser.net",
    "ecouser.net",
    "lb.ecouser.net",
    "lbo.ecouser.net",
    "msg-eu.ecouser.net",
    "portal-ww.ecouser.net",
    "portal-ww-qa1.ecouser.net",
    "portal-ww-qa.ecouser.net",
    "jmq-ngiot-eu.dc.robotww.ecouser.net",
    "api-app.ww.ecouser.net",
    "dc-as.app.ww.ecouser.net",
    "dc-eu.app.ww.ecouser.net",
    "dc-na.app.ww.ecouser.net",
    "area.ww.ecouser.net",
    "dc-as.base.ww.ecouser.net",
    "dc-eu.base.ww.ecouser.net",
    "dc-na.base.ww.ecouser.net",
    "cloud-ui.dc-as.cloud.ww.ecouser.net",
    "dc-as.cloud.ww.ecouser.net",
    "cloud-ui.dc-eu.cloud.ww.ecouser.net",
    "dc-eu.cloud.ww.ecouser.net",
    "cloud-ui.dc-na.cloud.ww.ecouser.net",
    "dc-na.cloud.ww.ecouser.net",
    "as.dc.ww.ecouser.net",
    "dc-as.ww.ecouser.net",
    "dc-aus.ww.ecouser.net",
    "dc.ww.ecouser.net",
    "api-app.dc-eu.ww.ecouser.net",
    "api-base.dc-eu.ww.ecouser.net",
    "api-ngiot.dc-eu.ww.ecouser.net",
    "dc-eu.ww.ecouser.net",
    "eis-nlp.dc-eu.ww.ecouser.net",
    "eu.dc.ww.ecouser.net",
    "users-base.dc-eu.ww.ecouser.net",
    "codepush-base.dc-na.ww.ecouser.net",
    "dc-na.ww.ecouser.net",
    "na.dc.ww.ecouser.net",
    "dc-as.ngiot.ww.ecouser.net",
    "dc-eu.ngiot.ww.ecouser.net",
    "dc-na.ngiot.ww.ecouser.net",
    "dc-as.rapp.ww.ecouser.net",
    "dc-eu.rapp.ww.ecouser.net",
    "dc-na.rapp.ww.ecouser.net",
    "dc-as.rop.ww.ecouser.net",
    "dc-eu.rop.ww.ecouser.net",
    "dc-na.rop.ww.ecouser.net",
    "ww.ecouser.net",
    "www.ecouser.net",
]


# Step 1: Build domain tree
def create_tree():
    tree = defaultdict(lambda: defaultdict(dict))

    for domain in domains:
        parts = domain.split(".")
        if len(parts) < 2:
            continue
        root = ".".join(parts[-2:])  # e.g., ecovacs.com
        subparts = parts[:-2]  # subdomains before the root
        current = tree[root]
        for part in reversed(subparts):
            current = current.setdefault(part, {})
    return tree


# Recursive function to display as indented tree
def print_tree(node, indent=0):
    output = []
    for key in sorted(node):
        output.append("  " * indent + f"- {key}")
        output.extend(print_tree(node[key], indent + 1))
    return output


# Step 2: Recursively create wildcard entries
def generate_wildcards(wildcard_set, node, parent_parts) -> None:
    if not node:
        # No children, wildcard parent
        if parent_parts:
            wildcard = "*." + ".".join(parent_parts)
            wildcard_set.add(wildcard)
        return

    # Node has children
    if parent_parts:
        wildcard = "*." + ".".join(parent_parts)
        wildcard_set.add(wildcard)

    for child in node:
        generate_wildcards(wildcard_set, node[child], [child, *parent_parts])


tree = create_tree()
wildcard_set = set()

# Print the final domain tree
for root in sorted(tree):
    print(f"\n{root}")
    print("\n".join(print_tree(tree[root], 1)))


# Process each root domain
for root in tree:
    wildcard_set.add(root)  # always include root domain itself
    generate_wildcards(wildcard_set, tree[root], [root])

# Step 3: Output sorted wildcard entries
for entry in sorted(wildcard_set):
    print(entry)
