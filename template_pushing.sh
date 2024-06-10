host="you_server"

for domain in domain.ru domain2.ru; do
	cat /etc/letsencrypt/live/${domain}/fullchain.pem | ssh root@$host fullchain ${domain} &&
	cat /etc/letsencrypt/live/${domain}/privkey.pem | ssh root@$host privkey ${domain} &&
	ssh root@$host restart nginx
done

